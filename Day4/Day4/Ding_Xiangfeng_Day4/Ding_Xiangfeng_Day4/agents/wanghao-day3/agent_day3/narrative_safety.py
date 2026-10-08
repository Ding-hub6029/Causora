"""Conservative lexical control for old free-text draft mode; not full semantic proof.
The new development selector has no model-authored prose at all.
"""
import re

NUMBER_WORDS=re.compile(r'\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|trillion|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|twentieth|thirtieth|fortieth|fiftieth|sixtieth|seventieth|eightieth|ninetieth|hundredth|twice|double|triple|half|quarter)\b',re.IGNORECASE)
CHINESE_NUMERALS='\u96f6\u3007\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u5343\u4e07\u4ebf\u4e24\u58f9\u8d30\u53c1\u8086\u4f0d\u9646\u67d2\u634c\u7396\u62fe\u4f70\u4edf'
CJK_QUANTITY=re.compile('(?:\u767e\u5206\u4e4b['+CHINESE_NUMERALS+']+|\u7b2c['+CHINESE_NUMERALS+r']+|['+CHINESE_NUMERALS+']+(?:\u4e2a\u6708|\u5e74|\u5468|\u5929|\u5c0f\u65f6|\u5206\u949f|\u7f8e\u5143|\u5143|\u5355\u4f4d|\u4ef6|\u6b21|\u500d|\u9879|\u4e2a))')


def assert_no_free_numeric_language(value:str):
    if any(c.isdigit() for c in value) or '{' in value or '}' in value or NUMBER_WORDS.search(value) or CJK_QUANTITY.search(value):
        raise ValueError('Narrative contains numeric language or a template; use code-bound references')
    return value
