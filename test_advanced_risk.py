#!/usr/bin/env python3
"""Test Advanced Risk Controller."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from execution.risk.advanced_risk_controller import AdvancedRiskController

def test_advanced_risk():
    risk = AdvancedRiskController(portfolio_value=100000)

    # Record some returns
    returns = [0.01, -0.02, 0.015, -0.005, 0.02, -0.01, 0.012]
    for r in returns:
        risk.record_return(r)

    # Set exposures
    risk.set_exposure('BTC', 0.30)
    risk.set_exposure('ETH', 0.20)
    risk.set_exposure('SOL', 0.10)

    # Get VaR
    var = risk.calculate_var(returns, 100000)
    print(f"VaR (95%): ${var.var_95:,.2f}")
    print(f"VaR (99%): ${var.var_99:,.2f}")

    # Check exposures
    limits = {'BTC': 0.35, 'ETH': 0.25, 'SOL': 0.15}
    ok, violations = risk.check_exposure_limits(limits)
    print(f"Exposures OK: {ok}")
    if violations:
        print(f"Violations: {violations}")

    # Get report
    report = risk.get_risk_report()
    print(f"Sharpe: {report['sharpe_ratio']:.2f}")
    print(f"Volatility: {report['volatility']:.2%}")

if __name__ == "__main__":
    test_advanced_risk()