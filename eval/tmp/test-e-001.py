import json

# ==========================================
# 1. DEFINE THE RUBRIC (Ground Truth)
# ==========================================
rubric = {
    "task_id": "IB-E-001",
    "criteria": {
        "key_1_location": {
            "description": "Must identify the Cash from Investing subtotal row or specific cells.",
            "accepted_values": [
                "Row 140",
                "140",
                "L140",
                "M140",
                "N140",
                "O140",
                "P140",
                "L140:P140",
                "Range 140",
                "Cells 140",
            ],
        },
        "key_3_formula": {
            "description": "Must include Row 138 (Maintenance Capex) in the sum.",
            "required_elements": ["138"],
            "forbidden_elements": ["#REF!", ""],
        },
    },
}

# ==========================================
# 2. DEFINE THE LLM OUTPUT (Simulated)
# ==========================================
llm_output_c = {
    "error_location": "Row 140 (Cash from Investing) - specifically cells L140, M140, N140",
    "current_formula": "=L139 (and similarly =M139, =N139 for subsequent years)",
    "corrected_formula": "=SUM(L138:L139) (and similarly =SUM(M138:M139), =SUM(N138:N139) for subsequent years)",
    "logical_explanation": "The Cash from Investing line (row 140) only captured Growth Capex (row 139) but omitted Maintenance Capex (row 138). Since Maintenance Capex is a cash outflow that reduces PP&E on the Balance Sheet, but was not flowing through the Cash Flow Statement to reduce Cash, Total Assets were overstated by the cumulative Maintenance Capex amount each period. This violated the Golden Rule that every Delta in non-cash assets must be reflected exactly once on the CFS.",
    "audit_steps_followed": [
        "Step 1: Identified the Break Year - Column L (2022) was the first year where Check row 123 showed non-zero variance of 33.87",
        "Step 2: Evaluated Error Behavior - Variance was variable/growing (33.87 -> 71.52 -> 113.40), indicating a Cash Flow Statement flow issue rather than a static Opening Balance error",
        "Step 3: Applied Half-Number Sign Check - Searched for 16.93 (half of 33.87) but found the variance exactly matched Maintenance Capex values, confirming an omission rather than a sign flip",
        "Step 4: Verified Golden Rule - Confirmed that Delta PP&E on Balance Sheet equaled Capex minus D&A, but Cash from Investing did not include Maintenance Capex, breaking the BS-CFS linkage",
        "Step 5: Verified Cash Link - Confirmed Balance Sheet Cash (row 100) correctly links to CFS EoP Cash (row 150), so the error propagated from the CFI line",
        "Step 6: Traced cumulative variance exactly matching cumulative Maintenance Capex across all projection years, confirming single source of error in row 140",
    ],
}

llm_output = {
    "error_location": "Row 148 – (+) Min. Cash Balance (Cash Flow Statement)",
    "current_formula": "=L166+L171",
    "corrected_formula": "=0",
    "logical_explanation": "Minimum Cash is already embedded in Ending Cash via the Cash Sweep mechanics. Adding it again as a financing inflow double-counts cash, inflating Total Liabilities & Equity without a corresponding increase in Assets. This produces a growing imbalance beginning in the first forecast year.",
    "audit_steps_followed": [
        "Variance Analysis – identified the first break year in the Balance Sheet check row",
        "Error Behavior Review – confirmed the variance grows over time, indicating a flow issue",
        "Linkage Integrity – verified the Ending Cash link from the Cash Flow Statement to the Balance Sheet",
        "Golden Rule Check – detected duplicate inclusion of Minimum Cash on the Cash Flow Statement",
    ],
}


# 3. THE EVALUATION FUNCTION
# ==========================================
def score_submission(rubric_data, llm_data):
    score = 0
    max_score = 2
    logs = []

    # --- CHECK 1: LOCATION ---
    # We check if any "accepted value" is inside the LLM's location string
    rubric_loc = rubric_data["criteria"]["key_1_location"]
    model_loc = str(llm_data.get("error_location", "")).upper()

    # Logic: substring match (case insensitive)
    if any(val.upper() in model_loc for val in rubric_loc["accepted_values"]):
        score += 1
        logs.append(f"✅ PASS: Location '{model_loc}' is correct.")
    else:
        logs.append(f"❌ FAIL: Location '{model_loc}' did not match allowed values.")

    # --- CHECK 2: FORMULA ---
    # We check for required ingredients (like '138') and forbidden ones (like '#REF!')
    rubric_form = rubric_data["criteria"]["key_3_formula"]
    model_form = str(llm_data.get("corrected_formula", ""))

    # 1. Forbidden Token Check
    forbidden_hit = next(
        (bad for bad in rubric_form["forbidden_elements"] if bad in model_form), None
    )

    # 2. Required Ingredient Check
    missing_req = [
        req for req in rubric_form["required_elements"] if req not in model_form
    ]

    if forbidden_hit:
        logs.append(f"❌ FAIL: Formula contained forbidden token: '{forbidden_hit}'")
    elif not missing_req:
        score += 1
        logs.append(
            f"✅ PASS: Formula contains all required ingredients: {rubric_form['required_elements']}"
        )
    else:
        logs.append(f"❌ FAIL: Formula is missing ingredients: {missing_req}")

    return {
        "final_score": f"{score}/{max_score}",
        "passed": score == max_score,
        "details": logs,
    }


# ==========================================
# 4. RUN CHECK
# ==========================================
if __name__ == "__main__":
    result = score_submission(rubric, llm_output)
    print(json.dumps(result, indent=2))
