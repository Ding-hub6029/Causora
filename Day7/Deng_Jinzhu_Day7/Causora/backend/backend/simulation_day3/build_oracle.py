"""Build a human-entered spreadsheet oracle; NEVER import simulation_day3.engine.

Constants below were independently derived from the synthetic contract and
manually specified tiny inventory paths. The formulas do not read simulation
outputs. Changing the engine cannot regenerate the oracle's expected values.
"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

OUT = Path(__file__).parent / "examples" / "day3_independent_oracle.xlsx"


def half_even(expression: str) -> str:
    """Excel formula for positive whole-dollar banker's rounding."""
    return f'=IF(MOD({expression},1)=0.5,IF(MOD(INT({expression}),2)=0,INT({expression}),INT({expression})+1),ROUND({expression},0))'


def build() -> None:
    book = Workbook()
    note = book.active
    note.title = "READ_ME"
    rows = [
        ("CAUSORA DAY 3 — INDEPENDENT MICRO ORACLE",),
        ("Not generated from a simulator, nor evidence of review/approval.",),
        ("Case 1: four runs with demand [10,0,0,0] in week 1; all later demand zero. Opening 0, target 2, 1-week B lead. D2 purchases B=2 for each run.",),
        ("Case 2: all 104 weeks zero demand; target 1, opening 0, A minimum 15600, D1 fixed 15600 A + 10400 B, D2 B=1.",),
        ("Source classification: 60%, 14% and $25k are synthetic Supplier A clause inputs. 26,000 forecast / renewal lock / model policy are demo assumptions, NOT signed facts.",),
        ("Excel formulas use half-even USD rounding. P90 = ascending nearest rank ceil(0.9*N); event = any stockout in 104 weeks.",),
        ("Expected literal checks (entered by hand): zero D0=$213408, D1=$344448, D2=$25013; one-in-four D2 probability=0.25, P90=$25025, TCO=$25037.",),
    ]
    for row in rows:
        note.append(row)
    note.column_dimensions["A"].width = 130
    note["A1"].font = Font(bold=True, size=16, color="FFFFFF")
    note["A1"].fill = PatternFill("solid", fgColor="17324D")
    for i in range(2, 8):
        note.cell(i, 1).alignment = Alignment(wrap_text=True, vertical="top")
        note.row_dimensions[i].height = 35

    zero = book.create_sheet("ZERO_DEMAND_104_WEEKS")
    zero.append(["Case: no fulfilled demand; no holding/loss. All amounts USD; no real recommendation."])
    zero.append(["D0 15,600 A minimum; D1 15,600 A/10,400 B; D2 buys 1 B and pays exit fee once."])
    zero.append(["Fee applied only on D2 and locked renewal; renewal premium on base A price only."])
    zero.append(["Option", "A units", "B units", "A base price", "B base price", "premium fraction", "exit fee", "base purchase", "renewal premium", "TCO", "literal expected TCO", "pass?"])
    for row, (name, a, b, fee, expected) in enumerate((
        ("D0", 15600, 0, 0, 213408),
        ("D1", 15600, 10400, 0, 344448),
        ("D2", 0, 1, 25000, 25013),
    ), 5):
        values = [name, a, b, 12, 12.6, 0.14, fee]
        for col, value in enumerate(values, 1):
            zero.cell(row, col, value)
        zero[f"H{row}"] = half_even(f"B{row}*D{row}+C{row}*E{row}")
        zero[f"I{row}"] = half_even(f"B{row}*D{row}*F{row}")
        zero[f"J{row}"] = f"=H{row}+I{row}+G{row}"
        zero[f"K{row}"] = expected
        zero[f"L{row}"] = f'=IF(J{row}=K{row},"PASS","FAIL")'

    four = book.create_sheet("FOUR_TRIALS_INDEPENDENT")
    four.append(["D2: first-week demand [10,0,0,0], later demand zero; B order=2, lead=7 days; no holding. Scenario target 10 makes reorder point 1 < stock target 2."])
    four.append(["Purchased base B units = 2; base cost = 2 × $12.6 = $25.2; rounded cash purchase = $25, termination fee = $25,000 once/trial."])
    four.append(["Independent expected results are literal cells below; engine values are not imported."])
    four.append(["trial", "week1 demand", "opening", "lost units", "stockout event", "B purchased", "base B price", "purchase raw", "purchase rounded", "cash rounded", "lost margin USD", "termination fee"])
    for row, demand in enumerate((10, 0, 0, 0), 5):
        four[f"A{row}"] = row - 4
        four[f"B{row}"] = demand
        four[f"C{row}"] = 0
        four[f"D{row}"] = f"=MAX(0,B{row}-C{row})"
        four[f"E{row}"] = f"=IF(D{row}>0,1,0)"
        four[f"F{row}"] = 2
        four[f"G{row}"] = 12.6
        four[f"H{row}"] = f"=F{row}*G{row}"
        four[f"I{row}"] = half_even(f"H{row}")
        four[f"L{row}"] = 25000
        four[f"J{row}"] = f"=I{row}+L{row}"
        four[f"K{row}"] = f"=D{row}*5"
    summary = [
        ("Stockout probability", "=SUM(E5:E8)/COUNT(E5:E8)", 0.25),
        ("P90 nearest rank cash", "=SMALL(J5:J8,ROUNDUP(0.9*COUNT(J5:J8),0))", 25025),
        ("Mean stockout loss rounded half-even", half_even("AVERAGE(K5:K8)"), 12),
        ("Purchase USD rounded from B=2", "=I5", 25),
        ("Exit fee USD exactly once", "=L5", 25000),
        ("Expected TCO (five lines)", "=B11+B12+B13", 25037),
    ]
    four.append(["Metric", "formula value", "literal expected", "pass?"])
    for row, (label, formula, literal) in enumerate(summary, 10):
        four.cell(row, 1, label)
        four.cell(row, 2, formula)
        four.cell(row, 3, literal)
        four.cell(row, 4, f'=IF(B{row}=C{row},"PASS","FAIL")')
    # Row 15 TCO combines rows 12+13+14, not probability/P90.
    four["B15"] = "=B12+B13+B14"
    four["C15"] = 25037
    for sheet in (zero, four):
        sheet.freeze_panes = "B5"
        for cell in sheet[4]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="17324D")
        for col in range(1, max(sheet.max_column, 12) + 1):
            sheet.column_dimensions[get_column_letter(col)].width = 19 if col > 1 else 35
        sheet.row_dimensions[1].height = 32
        sheet["A1"].alignment = Alignment(wrap_text=True)
    book.calculation.fullCalcOnLoad = True
    book.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
