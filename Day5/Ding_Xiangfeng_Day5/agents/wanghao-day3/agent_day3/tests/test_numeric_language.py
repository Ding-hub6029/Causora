import pytest
from agent_day3.narrative_safety import assert_no_free_numeric_language


@pytest.mark.parametrize('text',[
 'Tail cash is measured at the ninety percentile.',
 'The margin rose by fourteen percent.',
 'The term lasts twenty-four months.',
 'There are zero observations.',
 'Cash is twice the previous amount.',
 '\u5408\u540c\u671f\u9650\u4e3a\u4e8c\u5341\u56db\u4e2a\u6708\u3002',
 '\u4ef7\u683c\u4e0a\u6da8\u767e\u5206\u4e4b\u5341\u56db\u3002',
 '\u4f9b\u7ed9\u53d8\u5316\u4e3a\uff13\uff10\u5355\u4f4d\u3002',
 'The amount is {cash}.',
])
def test_numeric_language_cannot_hide_in_spelling(text):
    with pytest.raises(ValueError): assert_no_free_numeric_language(text)


def test_non_quantity_comparison_remains_possible():
    assert assert_no_free_numeric_language('Compare cost exposure and service tradeoffs with the referenced fields.')
