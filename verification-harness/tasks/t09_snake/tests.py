FUNCTION = "camel_to_snake"
DIFFICULTY = "medium"

CASES = [
    (("camelCase",), "camel_case"),
    (("CamelCase",), "camel_case"),
    (("HTTPServerError",), "http_server_error"),
    (("getHTTPResponseCode",), "get_http_response_code"),
    (("simple",), "simple"),
    (("ABC",), "abc"),
    (("version2Update",), "version2_update"),
    (("XMLParser2",), "xml_parser2"),
    (("HTML5Parser",), "html5_parser"),
    (("already_snake",), "already_snake"),
    (("A",), "a"),
    (("iPhone",), "i_phone"),
    (("",), ""),
    (("parseURLsFast",), "parse_ur_ls_fast"),
]
