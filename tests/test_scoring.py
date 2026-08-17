from services.scoring import _growth, _band

def test_growth():
    assert round(_growth(120, 100), 4) == 0.2

def test_band():
    assert _band(10) == "Low"
    assert _band(30) == "Normal"
    assert _band(50) == "Elevated"
    assert _band(70) == "High"
    assert _band(90) == "Very High"
