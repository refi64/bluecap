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

## Examples

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
$ bluecap untrust dart
# Set run default options (same as podman run arguments, but without --)
$ bluecap options-modify . 'tmpfs=/my-tmp'
# Show all options
$ bluecap options-dump .
# Persist the given directory
$ bluecap persistence -a '/home/cappy/.pub-cache'
# Remove it
$ bluecap persistence -r '/home/cappy/.pub-cache'
# Run it!
$ bluecap run dart echo '123'
# Export a command from inside the capsule
$ bluecap export dart pub
# Now we can do:
$ export PATH="$PATH:/var/lib/bluecap/exports/bin"
$ pub -h  # Same as 'bluecap run dart pub -h'
# Exports can be removed via a simple rm
$ sudo rm /var/lib/bluecap/exports/bin/pub
# Delete the capsule
$ bluecap delete dart
```
