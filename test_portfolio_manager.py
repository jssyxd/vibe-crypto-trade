"""
Test for Portfolio Manager.
"""

from portfolio.portfolio_manager import (
    PortfolioManager,
    AllocationStrategy,
    PortfolioStats,
    StrategyPosition,
)


def test_portfolio_manager_initialization():
    """Test portfolio manager initialization."""
    pm = PortfolioManager(initial_capital=100000, max_strategies=5)
    assert pm.initial_capital == 100000
    assert pm.max_strategies == 5
    assert pm.cash == 100000
    assert pm.allocation_strategy == AllocationStrategy.EQUAL_WEIGHT
    print("PASS: test_portfolio_manager_initialization")


def test_add_strategy_allocation():
    """Test adding strategy allocations."""
    pm = PortfolioManager()
    assert pm.add_strategy_allocation("strategy1", 0.2) is True
    assert pm.add_strategy_allocation("strategy2", 0.3) is True
    assert pm.add_strategy_allocation("invalid", 1.5) is False  # > 1.0
    assert pm.add_strategy_allocation("invalid", -0.1) is False  # < 0

    # Test max strategies limit
    pm2 = PortfolioManager(max_strategies=2)
    assert pm2.add_strategy_allocation("s1", 0.3) is True
    assert pm2.add_strategy_allocation("s2", 0.4) is True
    assert pm2.add_strategy_allocation("s3", 0.3) is False  # Exceeds max
    print("PASS: test_add_strategy_allocation")


def test_add_position():
    """Test adding positions."""
    pm = PortfolioManager(initial_capital=50000)
    assert pm.add_position("strat1", "BTC", 0.5, 40000) is True
    assert pm.cash == 50000 - 20000  # 0.5 * 40000 = 20000
    assert len(pm._positions) == 1

    # Test insufficient cash
    assert pm.add_position("strat1", "ETH", 10, 5000) is False
    print("PASS: test_add_position")


def test_update_position_price():
    """Test updating position prices."""
    pm = PortfolioManager(initial_capital=50000)
    pm.add_position("strat1", "BTC", 0.5, 40000)

    # Price goes up
    pm.update_position_price("strat1", "BTC", 45000)
    pos = pm._positions["strat1_BTC"]
    assert pos.current_price == 45000
    assert pos.unrealized_pnl == 0.5 * 5000  # 2500

    # Price goes down
    pm.update_position_price("strat1", "BTC", 35000)
    pos = pm._positions["strat1_BTC"]
    assert pos.unrealized_pnl == 0.5 * -5000  # -2500
    print("PASS: test_update_position_price")


def test_remove_position():
    """Test removing positions."""
    pm = PortfolioManager(initial_capital=50000)
    pm.add_position("strat1", "BTC", 0.5, 40000)
    cash_before = pm.cash

    assert pm.remove_position("strat1", "BTC") is True
    assert pm.cash == cash_before + 0.5 * 40000
    assert len(pm._positions) == 0

    # Remove non-existent
    assert pm.remove_position("strat1", "BTC") is False
    print("PASS: test_remove_position")


def test_calculate_rebalance_equal_weight():
    """Test rebalancing with equal weight strategy."""
    pm = PortfolioManager(allocation_strategy=AllocationStrategy.EQUAL_WEIGHT)
    pm.add_strategy_allocation("s1", 0.3)
    pm.add_strategy_allocation("s2", 0.4)
    pm.add_strategy_allocation("s3", 0.3)

    allocations = pm.calculate_rebalance()
    assert len(allocations) == 3
    for weight in allocations.values():
        assert abs(weight - 1/3) < 0.001
    print("PASS: test_calculate_rebalance_equal_weight")


def test_record_strategy_return():
    """Test recording strategy returns."""
    pm = PortfolioManager()
    pm.record_strategy_return("strat1", 0.05)
    pm.record_strategy_return("strat1", 0.03)
    pm.record_strategy_return("strat1", -0.02)

    assert len(pm._strategy_returns["strat1"]) == 3
    assert pm._strategy_returns["strat1"] == [0.05, 0.03, -0.02]
    print("PASS: test_record_strategy_return")


def test_get_strategy_correlation():
    """Test correlation calculation."""
    pm = PortfolioManager()

    # Perfect positive correlation
    pm.record_strategy_return("s1", 0.01)
    pm.record_strategy_return("s1", 0.02)
    pm.record_strategy_return("s1", 0.03)
    pm.record_strategy_return("s2", 0.01)
    pm.record_strategy_return("s2", 0.02)
    pm.record_strategy_return("s2", 0.03)

    corr = pm.get_strategy_correlation("s1", "s2")
    assert abs(corr - 1.0) < 0.001

    # Perfect negative correlation
    pm2 = PortfolioManager()
    pm2.record_strategy_return("s1", 0.01)
    pm2.record_strategy_return("s1", 0.02)
    pm2.record_strategy_return("s1", 0.03)
    pm2.record_strategy_return("s2", -0.01)
    pm2.record_strategy_return("s2", -0.02)
    pm2.record_strategy_return("s2", -0.03)

    corr = pm2.get_strategy_correlation("s1", "s2")
    assert abs(corr - (-1.0)) < 0.001

    # No correlation (insufficient data)
    pm3 = PortfolioManager()
    pm3.record_strategy_return("s1", 0.01)
    corr = pm3.get_strategy_correlation("s1", "s2")
    assert corr == 0.0
    print("PASS: test_get_strategy_correlation")


def test_get_portfolio_stats():
    """Test getting portfolio statistics."""
    pm = PortfolioManager(initial_capital=50000)
    pm.add_position("strat1", "BTC", 0.5, 40000)
    pm.update_position_price("strat1", "BTC", 45000)

    stats = pm.get_portfolio_stats()
    assert isinstance(stats, PortfolioStats)
    assert stats.cash == 50000 - 20000  # 0.5 * 40000
    assert stats.total_value == stats.cash + 2500  # unrealized pnl
    assert stats.total_pnl == stats.total_value - 50000
    print("PASS: test_get_portfolio_stats")


def test_get_strategy_positions():
    """Test getting strategy-specific positions."""
    pm = PortfolioManager(initial_capital=100000)
    pm.add_position("strat1", "BTC", 0.5, 40000)
    pm.add_position("strat1", "ETH", 2, 2500)
    pm.add_position("strat2", "SOL", 10, 100)

    strat1_positions = pm.get_strategy_positions("strat1")
    assert len(strat1_positions) == 2
    assert all(p.strategy_name == "strat1" for p in strat1_positions)

    strat2_positions = pm.get_strategy_positions("strat2")
    assert len(strat2_positions) == 1
    assert strat2_positions[0].symbol == "SOL"
    print("PASS: test_get_strategy_positions")


def test_momentum_weighted_allocation():
    """Test momentum-weighted allocation strategy."""
    pm = PortfolioManager(allocation_strategy=AllocationStrategy.MOMENTUM_WEIGHTED)
    pm.add_strategy_allocation("s1", 0.5)
    pm.add_strategy_allocation("s2", 0.5)

    # Strategy 1 has positive momentum
    pm.record_strategy_return("s1", 0.05)
    pm.record_strategy_return("s1", 0.06)
    pm.record_strategy_return("s1", 0.07)

    # Strategy 2 has negative momentum
    pm.record_strategy_return("s2", -0.02)
    pm.record_strategy_return("s2", -0.03)
    pm.record_strategy_return("s2", -0.04)

    allocations = pm.calculate_rebalance()
    # Strategy 1 should have higher weight
    assert allocations["s1"] > allocations["s2"]
    print("PASS: test_momentum_weighted_allocation")


def main():
    """Run all tests."""
    print("\n=== Portfolio Manager Tests ===\n")
    test_portfolio_manager_initialization()
    test_add_strategy_allocation()
    test_add_position()
    test_update_position_price()
    test_remove_position()
    test_calculate_rebalance_equal_weight()
    test_record_strategy_return()
    test_get_strategy_correlation()
    test_get_portfolio_stats()
    test_get_strategy_positions()
    test_momentum_weighted_allocation()
    print("\n=== All Tests Passed ===\n")


if __name__ == "__main__":
    main()