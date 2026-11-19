Write a Python function `camel_to_snake(name: str) -> str` that converts a camelCase or PascalCase
identifier to snake_case.

`name` contains only ASCII letters, digits and underscores. Insert an underscore:

1. between a lowercase letter or a digit and the uppercase letter that follows it
   (`"camelCase"` → `"camel_case"`, `"version2Update"` → `"version2_update"`), and
2. inside a run of uppercase letters, before the last uppercase letter of the run when that letter
   is followed by a lowercase letter, so acronyms stay together (`"HTTPServer"` → `"http_server"`).

Then convert the whole result to lowercase. Do not add any other underscores: a leading capital
does not produce a leading underscore, digits stay attached to the word before them, and an input
that is already snake_case is returned unchanged.

Examples:

- `camel_to_snake("getHTTPResponseCode")` → `"get_http_response_code"`
- `camel_to_snake("HTML5Parser")` → `"html5_parser"`
- `camel_to_snake("ABC")` → `"abc"`
