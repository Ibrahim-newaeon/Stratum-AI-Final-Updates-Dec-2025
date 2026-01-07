# =============================================================================
# Stratum AI - A/B Test Power Analysis & Sample Size Calculator
# =============================================================================
"""
Statistical power analysis for A/B testing experiments.

Provides:
- Sample size calculations for desired power
- Minimum detectable effect (MDE) calculations
- Power calculations for given sample sizes
- Sequential testing with early stopping
- Multiple testing corrections
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import math

import numpy as np
from scipy import stats

from app.core.logging import get_logger

logger = get_logger(__name__)


class TestType(str, Enum):
    """Type of statistical test."""
    TWO_SIDED = "two_sided"  # Test for any difference
    ONE_SIDED_GREATER = "one_sided_greater"  # Test if B > A
    ONE_SIDED_LESS = "one_sided_less"  # Test if B < A


class MetricType(str, Enum):
    """Type of metric being tested."""
    CONTINUOUS = "continuous"  # MAE, RMSE, etc.
    PROPORTION = "proportion"  # Conversion rate, CTR
    COUNT = "count"  # Number of events


@dataclass
class PowerAnalysisResult:
    """Result of a power analysis calculation."""
    sample_size_per_variant: int
    total_sample_size: int
    power: float
    alpha: float
    minimum_detectable_effect: float
    effect_type: str  # "absolute" or "relative"
    baseline_rate: Optional[float] = None
    days_to_significance: Optional[int] = None
    traffic_per_day: Optional[int] = None


@dataclass
class SequentialTestResult:
    """Result of a sequential test check."""
    should_stop: bool
    conclusion: str  # "winner_found", "no_difference", "continue"
    p_value: float
    adjusted_alpha: float
    samples_used: int
    spending_function: str


class ABPowerAnalyzer:
    """
    Power analysis and sample size calculator for A/B tests.

    Provides statistical rigor for experiment design and early stopping.

    Usage:
        analyzer = ABPowerAnalyzer()

        # Calculate required sample size
        result = analyzer.calculate_sample_size(
            baseline_rate=0.05,  # 5% conversion
            minimum_detectable_effect=0.1,  # 10% relative lift
            power=0.8,
            alpha=0.05,
        )
        print(f"Need {result.total_sample_size} samples")

        # Calculate power for a given sample size
        power = analyzer.calculate_power(
            sample_size_per_variant=5000,
            baseline_rate=0.05,
            minimum_detectable_effect=0.1,
        )

        # Check for early stopping
        stop_result = analyzer.sequential_test(
            successes_a=150, trials_a=3000,
            successes_b=180, trials_b=3000,
            planned_samples=10000,
        )
    """

    def __init__(self):
        # Default parameters
        self.default_alpha = 0.05
        self.default_power = 0.8

    # =========================================================================
    # Sample Size Calculations
    # =========================================================================

    def calculate_sample_size(
        self,
        baseline_rate: float,
        minimum_detectable_effect: float,
        power: float = 0.8,
        alpha: float = 0.05,
        test_type: TestType = TestType.TWO_SIDED,
        metric_type: MetricType = MetricType.PROPORTION,
        effect_is_relative: bool = True,
        baseline_std: Optional[float] = None,
        traffic_per_day: Optional[int] = None,
    ) -> PowerAnalysisResult:
        """
        Calculate required sample size for an A/B test.

        Args:
            baseline_rate: Current conversion rate (for proportions) or mean (for continuous)
            minimum_detectable_effect: The effect size you want to detect
            power: Desired statistical power (default 0.8 = 80%)
            alpha: Significance level (default 0.05 = 5%)
            test_type: Two-sided or one-sided test
            metric_type: Type of metric (proportion, continuous, count)
            effect_is_relative: If True, MDE is relative (e.g., 10% lift)
            baseline_std: Standard deviation (required for continuous metrics)
            traffic_per_day: Daily traffic (for estimating test duration)

        Returns:
            PowerAnalysisResult with sample size and related calculations
        """
        # Calculate absolute effect
        if effect_is_relative:
            absolute_effect = baseline_rate * minimum_detectable_effect
            effect_type = "relative"
        else:
            absolute_effect = minimum_detectable_effect
            effect_type = "absolute"

        # Get z-scores
        z_alpha = self._get_z_score(alpha, test_type)
        z_power = stats.norm.ppf(power)

        if metric_type == MetricType.PROPORTION:
            # Sample size for proportion test
            sample_size = self._sample_size_proportion(
                p1=baseline_rate,
                p2=baseline_rate + absolute_effect,
                z_alpha=z_alpha,
                z_power=z_power,
            )
        elif metric_type == MetricType.CONTINUOUS:
            if baseline_std is None:
                # Estimate std from baseline (common for MAE/RMSE)
                baseline_std = baseline_rate * 0.5  # Rough estimate

            sample_size = self._sample_size_continuous(
                mean_diff=absolute_effect,
                std=baseline_std,
                z_alpha=z_alpha,
                z_power=z_power,
            )
        else:
            # Count data - use Poisson approximation
            sample_size = self._sample_size_count(
                lambda1=baseline_rate,
                lambda2=baseline_rate + absolute_effect,
                z_alpha=z_alpha,
                z_power=z_power,
            )

        # Round up
        sample_size = int(math.ceil(sample_size))

        # Calculate days to significance
        days = None
        if traffic_per_day and traffic_per_day > 0:
            total_samples = sample_size * 2
            days = int(math.ceil(total_samples / traffic_per_day))

        return PowerAnalysisResult(
            sample_size_per_variant=sample_size,
            total_sample_size=sample_size * 2,
            power=power,
            alpha=alpha,
            minimum_detectable_effect=minimum_detectable_effect,
            effect_type=effect_type,
            baseline_rate=baseline_rate,
            days_to_significance=days,
            traffic_per_day=traffic_per_day,
        )

    def _sample_size_proportion(
        self,
        p1: float,
        p2: float,
        z_alpha: float,
        z_power: float,
    ) -> float:
        """Calculate sample size for proportion test."""
        # Pooled proportion
        p_pooled = (p1 + p2) / 2

        # Effect size (Cohen's h)
        h = 2 * (math.asin(math.sqrt(p2)) - math.asin(math.sqrt(p1)))

        if abs(h) < 1e-10:
            return float('inf')

        # Sample size formula
        n = 2 * ((z_alpha + z_power) / h) ** 2

        # Alternative formula (more conservative)
        numerator = (z_alpha * math.sqrt(2 * p_pooled * (1 - p_pooled)) +
                     z_power * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
        denominator = (p2 - p1) ** 2

        n_alt = numerator / denominator if denominator > 0 else float('inf')

        return max(n, n_alt)

    def _sample_size_continuous(
        self,
        mean_diff: float,
        std: float,
        z_alpha: float,
        z_power: float,
    ) -> float:
        """Calculate sample size for continuous metric test."""
        if abs(mean_diff) < 1e-10:
            return float('inf')

        # Cohen's d
        d = mean_diff / std

        # Sample size formula
        n = 2 * ((z_alpha + z_power) / d) ** 2

        return n

    def _sample_size_count(
        self,
        lambda1: float,
        lambda2: float,
        z_alpha: float,
        z_power: float,
    ) -> float:
        """Calculate sample size for count data (Poisson)."""
        if abs(lambda2 - lambda1) < 1e-10:
            return float('inf')

        # Sample size for Poisson rates
        numerator = (z_alpha * math.sqrt(2 * lambda1) +
                     z_power * math.sqrt(lambda1 + lambda2)) ** 2
        denominator = (lambda2 - lambda1) ** 2

        return numerator / denominator if denominator > 0 else float('inf')

    def _get_z_score(self, alpha: float, test_type: TestType) -> float:
        """Get z-score for given alpha and test type."""
        if test_type == TestType.TWO_SIDED:
            return stats.norm.ppf(1 - alpha / 2)
        else:
            return stats.norm.ppf(1 - alpha)

    # =========================================================================
    # Power Calculations
    # =========================================================================

    def calculate_power(
        self,
        sample_size_per_variant: int,
        baseline_rate: float,
        minimum_detectable_effect: float,
        alpha: float = 0.05,
        test_type: TestType = TestType.TWO_SIDED,
        metric_type: MetricType = MetricType.PROPORTION,
        effect_is_relative: bool = True,
        baseline_std: Optional[float] = None,
    ) -> float:
        """
        Calculate statistical power for a given sample size.

        Useful for understanding the probability of detecting
        an effect if it truly exists.
        """
        # Calculate absolute effect
        if effect_is_relative:
            absolute_effect = baseline_rate * minimum_detectable_effect
        else:
            absolute_effect = minimum_detectable_effect

        z_alpha = self._get_z_score(alpha, test_type)
        n = sample_size_per_variant

        if metric_type == MetricType.PROPORTION:
            p1 = baseline_rate
            p2 = baseline_rate + absolute_effect
            p_pooled = (p1 + p2) / 2

            # Standard error
            se = math.sqrt(p_pooled * (1 - p_pooled) * (2 / n))
            if se < 1e-10:
                return 1.0

            # Non-centrality parameter
            ncp = abs(p2 - p1) / se

        elif metric_type == MetricType.CONTINUOUS:
            if baseline_std is None:
                baseline_std = baseline_rate * 0.5

            se = baseline_std * math.sqrt(2 / n)
            if se < 1e-10:
                return 1.0

            ncp = abs(absolute_effect) / se

        else:
            # Count data
            lambda1 = baseline_rate
            lambda2 = baseline_rate + absolute_effect
            se = math.sqrt((lambda1 + lambda2) / n)
            if se < 1e-10:
                return 1.0

            ncp = abs(lambda2 - lambda1) / se

        # Calculate power
        power = 1 - stats.norm.cdf(z_alpha - ncp)

        return round(min(1.0, max(0.0, power)), 4)

    def calculate_mde(
        self,
        sample_size_per_variant: int,
        baseline_rate: float,
        power: float = 0.8,
        alpha: float = 0.05,
        test_type: TestType = TestType.TWO_SIDED,
        metric_type: MetricType = MetricType.PROPORTION,
        baseline_std: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Calculate the Minimum Detectable Effect for a given sample size.

        Returns both absolute and relative MDE.
        """
        z_alpha = self._get_z_score(alpha, test_type)
        z_power = stats.norm.ppf(power)
        n = sample_size_per_variant

        if metric_type == MetricType.PROPORTION:
            # Simplified formula for proportion
            se = math.sqrt(2 * baseline_rate * (1 - baseline_rate) / n)
            absolute_mde = (z_alpha + z_power) * se

        elif metric_type == MetricType.CONTINUOUS:
            if baseline_std is None:
                baseline_std = baseline_rate * 0.5
            se = baseline_std * math.sqrt(2 / n)
            absolute_mde = (z_alpha + z_power) * se

        else:
            se = math.sqrt(2 * baseline_rate / n)
            absolute_mde = (z_alpha + z_power) * se

        relative_mde = absolute_mde / baseline_rate if baseline_rate > 0 else 0

        return {
            "absolute_mde": round(absolute_mde, 6),
            "relative_mde_percent": round(relative_mde * 100, 2),
            "sample_size_per_variant": n,
            "baseline_rate": baseline_rate,
            "power": power,
            "alpha": alpha,
        }

    # =========================================================================
    # Sequential Testing
    # =========================================================================

    def sequential_test(
        self,
        successes_a: int,
        trials_a: int,
        successes_b: int,
        trials_b: int,
        planned_samples: int,
        alpha: float = 0.05,
        spending_function: str = "obrien_fleming",
        num_looks: int = 5,
        current_look: Optional[int] = None,
    ) -> SequentialTestResult:
        """
        Perform sequential testing with alpha spending.

        Allows for early stopping while controlling overall Type I error rate.

        Args:
            successes_a: Conversions in variant A
            trials_a: Total samples in variant A
            successes_b: Conversions in variant B
            trials_b: Total samples in variant B
            planned_samples: Total planned samples (both variants)
            alpha: Overall significance level
            spending_function: "obrien_fleming", "pocock", or "uniform"
            num_looks: Number of planned interim analyses
            current_look: Current interim look number (1 to num_looks)

        Returns:
            SequentialTestResult with stopping decision
        """
        total_samples = trials_a + trials_b

        # Determine current look based on samples collected
        if current_look is None:
            information_fraction = total_samples / planned_samples
            current_look = max(1, int(information_fraction * num_looks))

        # Calculate adjusted alpha for this look
        adjusted_alpha = self._calculate_spending(
            alpha=alpha,
            information_fraction=total_samples / planned_samples,
            spending_function=spending_function,
            num_looks=num_looks,
            current_look=current_look,
        )

        # Perform test
        p1 = successes_a / trials_a if trials_a > 0 else 0
        p2 = successes_b / trials_b if trials_b > 0 else 0

        # Two-proportion z-test
        p_pooled = (successes_a + successes_b) / (trials_a + trials_b) if (trials_a + trials_b) > 0 else 0
        se = math.sqrt(p_pooled * (1 - p_pooled) * (1/trials_a + 1/trials_b)) if p_pooled > 0 else 1

        z_stat = (p2 - p1) / se if se > 0 else 0
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))  # Two-sided

        # Decision
        if p_value < adjusted_alpha:
            if p2 > p1:
                conclusion = "variant_b_wins"
            else:
                conclusion = "variant_a_wins"
            should_stop = True
        elif total_samples >= planned_samples:
            conclusion = "no_difference"
            should_stop = True
        else:
            conclusion = "continue"
            should_stop = False

        return SequentialTestResult(
            should_stop=should_stop,
            conclusion=conclusion,
            p_value=round(p_value, 6),
            adjusted_alpha=round(adjusted_alpha, 6),
            samples_used=total_samples,
            spending_function=spending_function,
        )

    def _calculate_spending(
        self,
        alpha: float,
        information_fraction: float,
        spending_function: str,
        num_looks: int,
        current_look: int,
    ) -> float:
        """Calculate alpha spent at current look using spending function."""
        t = min(1.0, information_fraction)

        if spending_function == "obrien_fleming":
            # O'Brien-Fleming: Very conservative early, liberal later
            # α(t) = 2 - 2*Φ(z_α/2 / √t)
            z = stats.norm.ppf(1 - alpha / 2)
            spent = 2 * (1 - stats.norm.cdf(z / math.sqrt(t)))

        elif spending_function == "pocock":
            # Pocock: Linear spending
            # α(t) = α * log(1 + (e-1)*t)
            spent = alpha * math.log(1 + (math.e - 1) * t)

        else:  # uniform
            # Uniform: Equal alpha at each look
            spent = alpha * (current_look / num_looks)

        return min(alpha, spent)

    # =========================================================================
    # Multiple Testing Corrections
    # =========================================================================

    def bonferroni_correction(
        self,
        alpha: float,
        num_tests: int,
    ) -> float:
        """Apply Bonferroni correction for multiple testing."""
        return alpha / num_tests

    def holm_bonferroni(
        self,
        p_values: List[float],
        alpha: float = 0.05,
    ) -> List[Dict[str, Any]]:
        """
        Apply Holm-Bonferroni step-down correction.

        Less conservative than Bonferroni while controlling FWER.
        """
        n = len(p_values)
        sorted_indices = np.argsort(p_values)

        results = []
        rejected = False

        for i, idx in enumerate(sorted_indices):
            adjusted_alpha = alpha / (n - i)
            is_significant = p_values[idx] < adjusted_alpha and not rejected

            if not is_significant:
                rejected = True  # Stop rejecting once we fail

            results.append({
                "original_index": int(idx),
                "p_value": p_values[idx],
                "adjusted_alpha": round(adjusted_alpha, 6),
                "is_significant": is_significant,
            })

        # Sort back to original order
        results.sort(key=lambda x: x["original_index"])
        return results

    def benjamini_hochberg(
        self,
        p_values: List[float],
        alpha: float = 0.05,
    ) -> List[Dict[str, Any]]:
        """
        Apply Benjamini-Hochberg FDR correction.

        Controls False Discovery Rate rather than FWER.
        More powerful when running many tests.
        """
        n = len(p_values)
        sorted_indices = np.argsort(p_values)

        # Find the largest k where p(k) <= k/n * alpha
        max_significant = -1
        for k, idx in enumerate(sorted_indices, 1):
            if p_values[idx] <= (k / n) * alpha:
                max_significant = k

        results = []
        for i, idx in enumerate(sorted_indices):
            rank = i + 1
            critical_value = (rank / n) * alpha
            is_significant = rank <= max_significant

            results.append({
                "original_index": int(idx),
                "p_value": p_values[idx],
                "critical_value": round(critical_value, 6),
                "is_significant": is_significant,
            })

        results.sort(key=lambda x: x["original_index"])
        return results


# Singleton instance
power_analyzer = ABPowerAnalyzer()


# =============================================================================
# Convenience Functions
# =============================================================================

def calculate_ab_sample_size(
    baseline_conversion_rate: float,
    expected_lift_percent: float,
    power: float = 0.8,
    alpha: float = 0.05,
    daily_traffic: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Calculate required sample size for an A/B test.

    Args:
        baseline_conversion_rate: Current conversion rate (e.g., 0.05 for 5%)
        expected_lift_percent: Expected relative improvement (e.g., 10 for 10% lift)
        power: Desired statistical power (default 80%)
        alpha: Significance level (default 5%)
        daily_traffic: Optional daily traffic to estimate test duration

    Returns:
        Dict with sample size requirements and recommendations
    """
    result = power_analyzer.calculate_sample_size(
        baseline_rate=baseline_conversion_rate,
        minimum_detectable_effect=expected_lift_percent / 100,
        power=power,
        alpha=alpha,
        effect_is_relative=True,
        traffic_per_day=daily_traffic,
    )

    return {
        "sample_size_per_variant": result.sample_size_per_variant,
        "total_sample_size": result.total_sample_size,
        "baseline_rate": baseline_conversion_rate,
        "expected_lift_percent": expected_lift_percent,
        "power": power,
        "alpha": alpha,
        "days_to_significance": result.days_to_significance,
        "recommendation": (
            f"Run test for at least {result.days_to_significance} days "
            f"to detect a {expected_lift_percent}% lift with {power*100}% power"
            if result.days_to_significance else
            f"Need {result.total_sample_size:,} total samples"
        ),
    }


def check_test_power(
    current_samples_per_variant: int,
    baseline_rate: float,
    minimum_lift_percent: float,
) -> Dict[str, Any]:
    """
    Check if current sample size provides sufficient power.

    Returns current power and MDE for the given samples.
    """
    power = power_analyzer.calculate_power(
        sample_size_per_variant=current_samples_per_variant,
        baseline_rate=baseline_rate,
        minimum_detectable_effect=minimum_lift_percent / 100,
    )

    mde = power_analyzer.calculate_mde(
        sample_size_per_variant=current_samples_per_variant,
        baseline_rate=baseline_rate,
    )

    return {
        "samples_per_variant": current_samples_per_variant,
        "power_to_detect_target": power,
        "power_is_sufficient": power >= 0.8,
        "minimum_detectable_lift_percent": mde["relative_mde_percent"],
        "recommendation": (
            f"Current power is {power*100:.1f}%. "
            f"Can reliably detect effects ≥{mde['relative_mde_percent']:.1f}%."
        ),
    }
