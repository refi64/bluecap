#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from pathlib import Path

import argparse
import contextlib
import enum
import json
import os
import re
import shlex
import shutil
import subprocess
import sys


class Action(enum.Enum):
    CREATE = 'internal-create'
    DELETE = 'internal-delete'
    EXPORT = 'internal-export'
    MODIFY = 'internal-modify'
    PERSISTENCE = 'internal-persistence'
    RUN = 'internal-run'
    TRUST = 'internal-trust'
    UNTRUST = 'internal-untrust'


CAPSULE_REGEX = '[0-9a-zA-Z_.\-]+'
ETC_STORAGE = Path('/etc/bluecap')
GLOBAL_STORAGE = Path('/var/lib/bluecap')


@contextlib.contextmanager
def atomic_writer(target):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic = target.with_suffix(target.suffix + '.atomic')

    with atomic.open('w') as fp:
        yield fp

    atomic.rename(target)


def verify_capsule_name(capsule):
    if re.match(f'^{CAPSULE_REGEX}$', capsule) is None:
        sys.exit('Invalid capsule name.')


def get_capsule_path(capsule):
    verify_capsule_name(capsule)

    if capsule == '.':
        for root in (Path(), *Path().resolve().parents):
            path = (root / '.bluecap' / 'default.json').with_suffix('.json')
            if path.exists():
                return path.resolve()

    return (GLOBAL_STORAGE / 'capsules' / capsule).with_suffix('.json')


def resolve_capsule_name(capsule):
    path = get_capsule_path(capsule)
    if not path.exists():
        sys.exit('Invalid capsule.')

    return path.with_suffix('').name


def run(command):
    result = subprocess.run(command)
    if result.returncode:
        sys.exit(result.returncode)


def internal_create(name, image):
    run(['podman', 'pull', image])

    defaults_file = ETC_STORAGE / 'defaults.json'
    defaults = []

    if defaults_file.exists():
        with defaults_file.open() as fp:
            defaults = json.load(fp).get('options', [])
            if defaults is not None and not isinstance(defaults, list):
                sys.exit('defaults.json:options must be a list.')

    target = get_capsule_path(name)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        sys.exit('Capsule already exists.')

    with atomic_writer(target) as fp:
        json.dump({'image': image, 'options': defaults}, fp, indent=2)


def internal_delete(name):
    target = get_capsule_path(name)
    if not target.exists():
        sys.exit('Invalid capsule.')

    target.unlink()

    persistence = GLOBAL_STORAGE / 'persistence' / name
    if persistence.exists():
        shutil.rmtree(persistence)


def internal_modify(path, nadd, *args):
    path = Path(path)
    assert path.exists()

    nadd = int(nadd)
    add = args[:nadd]
    remove = args[nadd:]

    with path.open() as fp:
        capsule = json.load(fp)

    options = set(capsule['options'])
    options |= set(add)
    options -= set(remove)

    capsule['options'] = list(options)
    with atomic_writer(path) as fp:
        json.dump(capsule, fp, indent=2)


def persistence_path(capsule, path):
    path = Path(path)
    if path.is_absolute():
        path = Path(*path.parts[1:])

    return GLOBAL_STORAGE / 'persistence' / capsule / path


def internal_persistence(path, nadd, *args):
    path = Path(path)
    assert path.exists()
    capsule = path.with_suffix('').name

    nadd = int(nadd)
    add = args[:nadd]
    remove = args[nadd:]

    modify_add = []
    modify_remove = []

    for persist in add:
        location = persistence_path(capsule, persist)
        modify_add.append(f'volume={location}:{persist}:Z')
        location.mkdir(exist_ok=True, parents=True)
        os.chown(location, 1000, 1000)

    for unpersist in remove:
        location = persistence_path(capsule, unpersist)
        modify_remove.append(f'volume={location}:{unpersist}:Z')
        if location.exists():
            shutil.rmtree(location)

    internal_modify(path, len(modify_add), *modify_add, *modify_remove)


EXPORT_FILE = '''
#!/usr/bin/bluecap run-exported-internal:<NAME>
<COMMAND>
'''.lstrip()


def internal_export(capsule, prefix, command):
    exports = GLOBAL_STORAGE / 'exports' / 'bin'
    exports.mkdir(exist_ok=True, parents=True)

    contents = EXPORT_FILE.replace('<NAME>', prefix + capsule).replace('<COMMAND>', command)

    with (exports / os.path.basename(command)).open('w') as fp:
        fp.write(contents)
        os.fchmod(fp.fileno(), 0o755)


RULES_JS = '''
// THIS FILE IS AUTOMATICALLY GENERATED by bluecap
// Do NOT edit: your changes will be overwritten!

var TRUSTED = <TRUSTED>

polkit.addRule(function (action, subject) {
    if (action.id == 'com.refi64.Bluecap.run') {
        var cmdline = action.lookup('command_line')
        var capsule = cmdline.match(/internal-run (\S+)/)[1]
        polkit.log('bluecap:' + capsule)
        if (!capsule.match(/^<REGEX>$/))
            return polkit.Result.NO
        if (TRUSTED.hasOwnProperty(capsule))
            return polkit.Result.YES
    }

    return polkit.Result.NOT_HANDLED
});
'''.lstrip()


def internal_trust(action, name):
    trust_list = GLOBAL_STORAGE / 'polkit-list.json'
    rules = Path('/etc/polkit-1/rules.d/49-bluecap.rules')

    trusted = set()
    if trust_list.exists():
        with trust_list.open() as fp:
            trusted = set(json.load(fp)['trusted'])

    if action == Action.TRUST:
        trusted.add(name)
    elif action == Action.UNTRUST:
        trusted.remove(name)

    trusted_js = json.dumps({name: True for name in trusted})
    rules_js = RULES_JS\
        .replace('<TRUSTED>', trusted_js)\
        .replace('<REGEX>', CAPSULE_REGEX)

    with atomic_writer(trust_list) as list_fp:
        json.dump({'trusted': list(trusted)}, list_fp, indent=2)
        list_fp.flush()

        with atomic_writer(rules) as rules_fp:
            rules_fp.write(rules_js)
            rules_fp.flush()


def internal_run(capsule, cwd, command):
    path = get_capsule_path(capsule)
    if not path.exists():
        sys.exit('Invalid capsule.')

    with path.open() as fp:
        capsule = json.load(fp)

    image = capsule['image']
    options = [f'--{opt}' for opt in capsule['options']]

    if cwd != '':
        cwd = Path(cwd)
        options.extend((f'--volume={cwd}:/var/work/{cwd.name}:Z',
                        f'--workdir=/var/work/{cwd.name}'))

    os.execvp('podman', ['podman', 'run', '--rm', *options, image, 'sh', '-c',
                         'useradd cappy -o -u 1000 && exec su -c "env PATH=\'$PATH\' $0" cappy',
                         command])


def run_exported_internal(capsule, export, *args):
    with open(export) as fp:
        while True:
            line = fp.readline().strip()
            if line and not line.startswith('#!'):
                break
        else:
            sys.exit('Invalid export file.')

    command = [line, *args]

    if capsule.startswith('.'):
        cwd = Path().resolve()
        capsule = capsule[1:]
    else:
        cwd = ''

    redirect(Action.RUN, resolve_capsule_name(capsule), cwd, ' '.join(map(shlex.quote, command)))


def redirect(action, *args):
    run(['pkexec', '/usr/bin/bluecap', action.value, *args])


def exec_create(args):
    verify_capsule_name(args.capsule)
    redirect(Action.CREATE, args.capsule, args.image)


def exec_delete(args):
    verify_capsule_name(args.capsule)
    redirect(Action.DELETE, args.capsule)


def exec_link(args):
    path = get_capsule_path(args.capsule)
    if not path.exists():
        sys.exit('Invalid capsule.')

    linkdir = Path() / '.bluecap'
    linkdir.mkdir(parents=True, exist_ok=True)

    link = linkdir / 'default.json'
    if link.exists():
        link.unlink()
    link.symlink_to(path)


def exec_trust(args):
    redirect(Action.TRUST, resolve_capsule_name(args.capsule))


def exec_untrust(args):
    redirect(Action.UNTRUST, resolve_capsule_name(args.capsule))


def exec_options_modify(args):
    path = get_capsule_path(args.capsule)
    if not path.exists():
        sys.exit('Invalid capsule.')

    redirect(Action.MODIFY, path, str(len(args.add)), *args.add, *args.remove)


def exec_options_dump(args):
    path = get_capsule_path(args.capsule)
    if not path.exists():
        sys.exit('Invalid capsule.')

    print(path.read_text())


def exec_persistence(args):
    path = get_capsule_path(args.capsule)
    if not path.exists():
        sys.exit('Invalid capsule.')

    redirect(Action.PERSISTENCE, path, str(len(args.add)), *args.add, *args.remove)


def exec_export(args):
    if args.capsule == '.':
        prefix = '.'
    else:
        prefix = ''

    redirect(Action.EXPORT, resolve_capsule_name(args.capsule), prefix, args.command)


def exec_run(args):
    if args.capsule == '.':
        cwd = Path().resolve()
    else:
        cwd = ''

    redirect(Action.RUN, resolve_capsule_name(args.capsule), cwd,
             ' '.join(map(shlex.quote, args.command)))


def main():
    if len(sys.argv) > 1:
        if sys.argv[1].startswith('internal-'):
            action = Action(sys.argv[1])
            args = sys.argv[2:]
            if action == Action.CREATE:
                internal_create(*args)
            elif action == Action.DELETE:
                internal_delete(*args)
            elif action == Action.MODIFY:
                internal_modify(*args)
            elif action == Action.PERSISTENCE:
                internal_persistence(*args)
            elif action == Action.EXPORT:
                internal_export(*args)
            elif action in (Action.TRUST, Action.UNTRUST):
                internal_trust(action, *args)
            elif action == Action.RUN:
                internal_run(*args)
            else:
                sys.exit('Invalid internal capsule command.')

            return
        elif sys.argv[1].startswith('run-exported-internal:'):
            run_exported_internal(sys.argv[1].split(':', 1)[1], *sys.argv[2:])
            return

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='Commands:')

    create_command = subparsers.add_parser('create', help='Create a capsule')
    create_command.add_argument('capsule', help='The new capsule name')
    create_command.add_argument('image', help='The image to use to create the capsule')
    create_command.set_defaults(func=exec_create)

    delete_command = subparsers.add_parser('delete', help='Delete a capsule')
    delete_command.add_argument('capsule', help='The capsule to delete')
    delete_command.set_defaults(func=exec_delete)

    link_command = subparsers.add_parser('link', help='Link the capsule into the current '
                                                      'directory')
    link_command.add_argument('capsule', help='The capsule to link')
    link_command.set_defaults(func=exec_link)

    trust_command = subparsers.add_parser('trust',
                                          help='Add a policy allowing normal users to '
                                               'run the given capsule.')
    trust_command.add_argument('capsule', help='The capsule to add the policy for')
    trust_command.set_defaults(func=exec_trust)

    untrust_command = subparsers.add_parser('untrust', help='Remove the policy for'
                                                            ' the given capsule')
    untrust_command.add_argument('capsule', help='The capsule to remove the policy for')
    untrust_command.set_defaults(func=exec_untrust)

    options_modify_command = subparsers.add_parser('options-modify',
                                                   help='Modify the capsule options')
    options_modify_command.add_argument('capsule', help='The capsule')
    options_modify_command.add_argument('--add', '-a', help='', nargs='*', default=[])
    options_modify_command.add_argument('--remove', '-r', help='', nargs='*', default=[])
    options_modify_command.set_defaults(func=exec_options_modify)

    options_dump_command = subparsers.add_parser('options-dump', help='')
    options_dump_command.add_argument('capsule', help='The capsule')
    options_dump_command.set_defaults(func=exec_options_dump)

    persistence_command = subparsers.add_parser('persistence', help='')
    persistence_command.add_argument('capsule', help='The capsule')
    persistence_command.add_argument('--add', '-a', help='', nargs='*', default=[])
    persistence_command.add_argument('--remove', '-r', help='', nargs='*', default=[])
    persistence_command.set_defaults(func=exec_persistence)

    export_command = subparsers.add_parser('export', help='')
    export_command.add_argument('capsule', help='The capsule')
    export_command.add_argument('command', help='The command to export')
    export_command.set_defaults(func=exec_export)

    run_command = subparsers.add_parser('run', help='Run a capsule')
    run_command.add_argument('capsule', help='The capsule')
    run_command.add_argument('command', help='The command to run', nargs='+')
    run_command.set_defaults(func=exec_run)

    args = parser.parse_args()
    if not hasattr(args, 'func'):
        sys.exit('A command is required.')

    args.func(args)

if __name__ == '__main__':
    main()
