# TODO

- sort out export task and export task results schema

## Type Checking

- [ ] Sort out type checking in `eval/run.py` - `load_config()` returns `dict`
      which causes `config.get()` to return `Unknown`. Fix by returning
      `dict[str, Any]` or using a TypedDict.
