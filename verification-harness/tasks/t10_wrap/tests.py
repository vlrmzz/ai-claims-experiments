FUNCTION = "word_wrap"
DIFFICULTY = "medium"

CASES = [
    (("the quick brown fox", 10), ["the quick", "brown fox"]),
    (("", 5), []),
    (("   ", 5), []),
    (("hello", 5), ["hello"]),
    (("hello world", 5), ["hello", "world"]),
    (("a b c d e", 3), ["a b", "c d", "e"]),
    (("supercalifragilistic is long", 6), ["superc", "alifra", "gilist", "ic is", "long"]),
    (("hi abcdefgh", 4), ["hi", "abcd", "efgh"]),
    (("one  two\nthree\tfour", 9), ["one two", "three", "four"]),
    (("abcdef gh", 3), ["abc", "def", "gh"]),
    (("ab cdefgh ij", 3), ["ab", "cde", "fgh", "ij"]),
    (("x abcdefg y", 3), ["x", "abc", "def", "g y"]),
]
