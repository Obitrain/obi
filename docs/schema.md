# Discovering the API

`obi schema` searches the OpenAPI contract bundled with the installed CLI. It does not require
authentication or network access.

## List API areas

```bash
obi schema tags
```

This lists the available OpenAPI tags and the number of operations under each one.

## Search operations

```bash
obi schema list
obi schema list --grep session
obi schema list --tag "Session endpoint"
```

`--grep` searches operation paths, IDs, summaries, tags, parameter names, enum values, referenced
schema names, and schema property names.

Use `--tag` when you already know the API area. Both filters can be combined.

## Inspect an operation

```bash
obi schema show /v1/training/sessions -X GET
```

The result includes:

- HTTP method, path, operation ID, tags, and summary
- path, query, header, and cookie parameters
- request-body schemas
- response schemas
- complete definitions for referenced component schemas

If a path supports only one method, `-X` is optional. If it supports several, pass `-X` to select
one:

```bash
obi schema show /v1/user -X PATCH
```

You can also pass an operation ID or a concrete path matching an OpenAPI template:

```bash
obi schema show Modify_information_about_the_user_v1_user_patch
obi schema show /v1/stats/activity/weekly
```

## Machine-readable output

All schema commands support `--json` and `-o`:

```bash
obi schema list --grep distance --json
obi schema show /v1/user -X GET -o yaml
```

The contract is a snapshot shipped with each `obi` release. Upgrade `obitrain` to get a newer
snapshot when the API changes.
