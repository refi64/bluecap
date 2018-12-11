# bluecap

A lightweight wrapper over podman that makes it easier to have container-based workflows.
The idea was conceived when I switched to Fedora Silverblue and realized I didn't particularly
like the way my development workflow was working out...

The general idea behind bluecap is to create temporary containers that are immediately
discarded immediately after use. It's not quite the best code I've ever written, nor is it
the most powerful/general-purpose...but hey, it works!

## Features

- Easy to create "capsules", which are specifications for a container that will be created
  and immediately destroyed after use.
- Possible to associate a capsule with the current directory.
- Automatically binds the current directory.
- Handles persisting paths across container creations.
- Allows you to "trust" a capsule, meaning that a root password won't be required to run it.

That being said, note that this may have security issues when trusted containers!! If you'd
rather not risk it, don't use `bluecap trust`.

## Installation

### Fedora Workstation

```bash
dnf copr enable refi64/bluecap
dnf install bluecap
```

### Fedora Silverblue

You can install `dnf` and then run:

```bash
dnf copr enable refi64/bluecap
rpm-ostree install bluecap
```

Otherwise, you can add the repo manually:

```bash
curl -L "https://copr.fedorainfracloud.org/coprs/refi64/bluecap/repo/fedora-`lsb_release -rs`/refi64-bluecap-fedora-`lsb_release -rs`.repo" | sudo tee /etc/yum.repos.d/_copr_refi64-bluecap.repo
rpm-ostree install bluecap
```

## Building from source

Use `nimble config` to configure bluecap:

```
# Default prefix (/usr), bindir (/usr/bin), datadir (/usr/share), and sysconfdir (/etc).
$ nimble config
# Set the prefix (this will also set bindir=/usr/local/bin and datadir=/usr/local/share)
$ nimble config destdir=my-build-directory prefix=/usr/local
# All the others can be set in a similar manner
```

Then, run `nimble build` and `nimble sysinstall`:

```
$ nimble build
$ nimble sysinstall
# Install into a different destdir:
$ nimble sysinstall my-custom-destdir
```

## Examples

**NOTE:** This is for the 0.3 alpha. For v0.2, see the README on that Git tag.

```bash
# Create a new capsule
$ bluecap create dart google/dart
# Link the capsule into the current directory (in .bluecap/default.json)
$ bluecap link dart
# "Trust" the container
$ bluecap trust dart
# Same as above (since we linked it)
$ bluecap trust .
# Untrust it
$ bluecap trust -u dart
# Set run default options (same as podman run arguments, but without --)
$ bluecap options-modify . 'tmpfs=/my-tmp'
# Show all options
$ bluecap options-dump .
# Remove an option
$ bluecap options-modify -r dart 'net=host'
# Persist the given directory
$ bluecap persistence '/var/data/.pub-cache'
# Remove it
$ bluecap persistence -r '/var/data/.pub-cache'
# Run it!
$ bluecap run dart echo -e '1\n2\n3'
# Export a command from inside the capsule
$ bluecap export dart pub
# Now we can do:
$ export PATH="$PATH:/var/lib/bluecap/exports/bin"
$ pub -h  # Same as 'bluecap run dart pub -h'
# Exports can be removed via a simple rm
$ sudo rm /var/lib/bluecap/exports/bin/pub
# Delete the capsule
$ bluecap delete dart
# Delete the capsule, but keep its persisted files (/var/lib/bluecap/persistence/CAPSULE-NAME)
$ bluecap delete -k dart
```
