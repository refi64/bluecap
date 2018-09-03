# bluecap

A lightweight wrapper over podman that makes it easier to have container-based workflows.

The general idea behind bluecap is to create temporary containers that are immediately
discarded immediately after use.

## Examples

```bash
# Create a new container
$ bluecap new dart google/dart
# Link the container into the current directory (in .bluecap/default.json)
$ bluecap link dart
# Other name
$ bluecap link dart other-name
# Ensure that a new user is created, and allow the container to be run without root
# (note that permission is still required to configure it)
$ bluecap policy-add .
# Set run default options
$ bluecap options-add . mount='name='
# Easy volume shorthand
$ bluecap add-persistent-volume . '/home/cappy/.pub-cache'
# Run it!
$ bluecap run dart
```

```bash
$ bluecap new dart google/dart
```
