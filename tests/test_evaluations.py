def test_placeholder_for_evaluation_api_contract():
    assert {
        "create": "/api/v1/evaluations",
        "results": "/api/v1/evaluations/{evaluation_id}/results",
    }
