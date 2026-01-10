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


# =============================================================================
# Bayesian A/B Testing
# =============================================================================

@dataclass
class BayesianTestResult:
    """Result of Bayesian A/B test analysis."""
    probability_b_beats_a: float
    probability_a_beats_b: float
    expected_loss_choosing_b: float
    expected_loss_choosing_a: float
    credible_interval_a: Tuple[float, float]
    credible_interval_b: Tuple[float, float]
    lift_credible_interval: Tuple[float, float]
    recommendation: str
    samples_a: int
    samples_b: int
    posterior_mean_a: float
    posterior_mean_b: float


class BayesianABTester:
    """
    Bayesian A/B testing with Beta-Binomial model.

    Provides probability-based interpretation of test results
    and expected loss calculations for decision making.

    Advantages over frequentist testing:
    - Natural interpretation: "Probability B beats A"
    - No fixed sample size required
    - Incorporates prior knowledge
    - Expected loss calculations for ROI decisions
    """

    def __init__(
        self,
        prior_alpha: float = 1.0,  # Beta prior: uniform by default
        prior_beta: float = 1.0,
        credible_level: float = 0.95,
    ):
        """
        Initialize Bayesian tester.

        Args:
            prior_alpha: Alpha parameter of Beta prior
            prior_beta: Beta parameter of Beta prior
            credible_level: Credible interval level (default 95%)
        """
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
        self.credible_level = credible_level

    def analyze(
        self,
        successes_a: int,
        trials_a: int,
        successes_b: int,
        trials_b: int,
        value_per_conversion: float = 1.0,
        num_samples: int = 100000,
    ) -> BayesianTestResult:
        """
        Perform Bayesian analysis of A/B test.

        Args:
            successes_a: Conversions in variant A
            trials_a: Total samples in variant A
            successes_b: Conversions in variant B
            trials_b: Total samples in variant B
            value_per_conversion: Revenue per conversion (for loss calculation)
            num_samples: Monte Carlo samples for probability calculation

        Returns:
            BayesianTestResult with probabilities and recommendations
        """
        # Posterior parameters (Beta-Binomial conjugate)
        alpha_a = self.prior_alpha + successes_a
        beta_a = self.prior_beta + trials_a - successes_a
        alpha_b = self.prior_alpha + successes_b
        beta_b = self.prior_beta + trials_b - successes_b

        # Monte Carlo sampling
        samples_a = np.random.beta(alpha_a, beta_a, num_samples)
        samples_b = np.random.beta(alpha_b, beta_b, num_samples)

        # Probability B beats A
        prob_b_beats_a = np.mean(samples_b > samples_a)
        prob_a_beats_b = 1 - prob_b_beats_a

        # Expected loss (opportunity cost of wrong decision)
        # Loss of choosing B when A is better
        loss_b = np.maximum(samples_a - samples_b, 0) * value_per_conversion
        expected_loss_b = np.mean(loss_b)

        # Loss of choosing A when B is better
        loss_a = np.maximum(samples_b - samples_a, 0) * value_per_conversion
        expected_loss_a = np.mean(loss_a)

        # Posterior means
        posterior_mean_a = alpha_a / (alpha_a + beta_a)
        posterior_mean_b = alpha_b / (alpha_b + beta_b)

        # Credible intervals
        ci_level = (1 - self.credible_level) / 2
        ci_a = (
            float(np.percentile(samples_a, ci_level * 100)),
            float(np.percentile(samples_a, (1 - ci_level) * 100)),
        )
        ci_b = (
            float(np.percentile(samples_b, ci_level * 100)),
            float(np.percentile(samples_b, (1 - ci_level) * 100)),
        )

        # Lift credible interval
        lift_samples = (samples_b - samples_a) / samples_a
        lift_ci = (
            float(np.percentile(lift_samples, ci_level * 100)),
            float(np.percentile(lift_samples, (1 - ci_level) * 100)),
        )

        # Generate recommendation
        recommendation = self._generate_recommendation(
            prob_b_beats_a, expected_loss_a, expected_loss_b, value_per_conversion
        )

        return BayesianTestResult(
            probability_b_beats_a=round(prob_b_beats_a, 4),
            probability_a_beats_b=round(prob_a_beats_b, 4),
            expected_loss_choosing_b=round(expected_loss_b, 4),
            expected_loss_choosing_a=round(expected_loss_a, 4),
            credible_interval_a=ci_a,
            credible_interval_b=ci_b,
            lift_credible_interval=lift_ci,
            recommendation=recommendation,
            samples_a=trials_a,
            samples_b=trials_b,
            posterior_mean_a=round(posterior_mean_a, 6),
            posterior_mean_b=round(posterior_mean_b, 6),
        )

    def _generate_recommendation(
        self,
        prob_b_beats_a: float,
        loss_a: float,
        loss_b: float,
        value: float,
    ) -> str:
        """Generate actionable recommendation."""
        if prob_b_beats_a >= 0.95:
            return "Strong evidence B is better. Recommend implementing B."
        elif prob_b_beats_a >= 0.90:
            return "Good evidence B is better. Consider implementing B with monitoring."
        elif prob_b_beats_a >= 0.75:
            return "Moderate evidence B is better. Continue testing for more certainty."
        elif prob_b_beats_a <= 0.05:
            return "Strong evidence A is better. Recommend keeping A."
        elif prob_b_beats_a <= 0.10:
            return "Good evidence A is better. Consider keeping A."
        elif prob_b_beats_a <= 0.25:
            return "Moderate evidence A is better. Continue testing for more certainty."
        else:
            return "No clear winner yet. Continue testing."

    def calculate_stopping_threshold(
        self,
        min_sample_per_variant: int = 100,
        max_sample_per_variant: int = 10000,
        probability_threshold: float = 0.95,
        loss_threshold: float = 0.001,
    ) -> Dict[str, Any]:
        """
        Calculate when to stop based on probability or loss thresholds.

        Returns guidelines for early stopping decisions.
        """
        return {
            "stop_for_winner": f"Stop when P(B beats A) ≥ {probability_threshold:.0%} or P(A beats B) ≥ {probability_threshold:.0%}",
            "stop_for_no_difference": f"Stop when expected loss < {loss_threshold} for either choice",
            "minimum_samples": min_sample_per_variant,
            "maximum_samples": max_sample_per_variant,
            "recommendation": (
                f"Run until min {min_sample_per_variant} samples per variant, "
                f"then evaluate weekly until threshold met or max reached."
            ),
        }


# =============================================================================
# CUPED Variance Reduction
# =============================================================================

@dataclass
class CUPEDResult:
    """Result of CUPED variance reduction."""
    original_variance: float
    adjusted_variance: float
    variance_reduction_percent: float
    original_effect: float
    adjusted_effect: float
    theta: float  # Adjustment coefficient
    effective_sample_increase: float  # Equivalent sample size boost


class CUPEDAnalyzer:
    """
    CUPED (Controlled-experiment Using Pre-Experiment Data) variance reduction.

    Uses pre-experiment covariate data to reduce variance in A/B test metrics,
    effectively increasing statistical power without more samples.

    Based on Microsoft's CUPED paper: "Improving the Sensitivity of Online
    Controlled Experiments by Utilizing Pre-Experiment Data"
    """

    def __init__(self):
        pass

    def apply_cuped(
        self,
        metric_a: np.ndarray,
        metric_b: np.ndarray,
        covariate_a: np.ndarray,
        covariate_b: np.ndarray,
    ) -> CUPEDResult:
        """
        Apply CUPED adjustment to reduce metric variance.

        Args:
            metric_a: Post-experiment metric values for variant A
            metric_b: Post-experiment metric values for variant B
            covariate_a: Pre-experiment covariate for variant A
            covariate_b: Pre-experiment covariate for variant B

        Returns:
            CUPEDResult with variance reduction metrics
        """
        # Combine data
        metric = np.concatenate([metric_a, metric_b])
        covariate = np.concatenate([covariate_a, covariate_b])

        # Calculate theta (optimal adjustment coefficient)
        cov_xy = np.cov(covariate, metric)[0, 1]
        var_x = np.var(covariate)
        theta = cov_xy / var_x if var_x > 0 else 0

        # Calculate global covariate mean
        covariate_mean = np.mean(covariate)

        # Adjust metrics
        adjusted_a = metric_a - theta * (covariate_a - covariate_mean)
        adjusted_b = metric_b - theta * (covariate_b - covariate_mean)

        # Calculate variances
        original_var_a = np.var(metric_a)
        original_var_b = np.var(metric_b)
        adjusted_var_a = np.var(adjusted_a)
        adjusted_var_b = np.var(adjusted_b)

        # Combined variance
        n_a, n_b = len(metric_a), len(metric_b)
        original_variance = (original_var_a / n_a + original_var_b / n_b)
        adjusted_variance = (adjusted_var_a / n_a + adjusted_var_b / n_b)

        # Variance reduction
        reduction = (original_variance - adjusted_variance) / original_variance if original_variance > 0 else 0

        # Effect estimates
        original_effect = np.mean(metric_b) - np.mean(metric_a)
        adjusted_effect = np.mean(adjusted_b) - np.mean(adjusted_a)

        # Effective sample increase
        # If variance reduced by X%, it's like having 1/(1-X) times the samples
        effective_sample_increase = 1 / (1 - reduction) if reduction < 1 else 1

        return CUPEDResult(
            original_variance=round(original_variance, 6),
            adjusted_variance=round(adjusted_variance, 6),
            variance_reduction_percent=round(reduction * 100, 2),
            original_effect=round(original_effect, 6),
            adjusted_effect=round(adjusted_effect, 6),
            theta=round(theta, 6),
            effective_sample_increase=round(effective_sample_increase, 2),
        )

    def estimate_power_boost(
        self,
        correlation: float,
    ) -> Dict[str, float]:
        """
        Estimate power boost from CUPED given covariate correlation.

        Higher correlation = more variance reduction = higher power.
        """
        # Variance reduction is approximately r^2
        variance_reduction = correlation ** 2

        # Effective sample multiplier
        sample_multiplier = 1 / (1 - variance_reduction) if variance_reduction < 1 else 1

        return {
            "correlation": correlation,
            "expected_variance_reduction_percent": round(variance_reduction * 100, 1),
            "effective_sample_multiplier": round(sample_multiplier, 2),
            "recommendation": (
                f"With correlation {correlation:.2f}, CUPED can reduce variance by ~{variance_reduction*100:.0f}%, "
                f"equivalent to {sample_multiplier:.1f}x more samples."
            ),
        }


# =============================================================================
# Multi-Armed Bandit
# =============================================================================

@dataclass
class BanditArm:
    """State of a bandit arm."""
    arm_id: str
    successes: int
    failures: int
    total_pulls: int
    estimated_value: float
    ucb_value: float


class ThompsonSamplingBandit:
    """
    Thompson Sampling multi-armed bandit for adaptive experimentation.

    Unlike fixed-split A/B tests, Thompson Sampling:
    - Adapts traffic allocation based on performance
    - Minimizes regret (opportunity cost of suboptimal choices)
    - Naturally handles many variants
    """

    def __init__(self, arm_ids: List[str], prior_alpha: float = 1.0, prior_beta: float = 1.0):
        """
        Initialize bandit with arm IDs.

        Args:
            arm_ids: List of variant identifiers
            prior_alpha: Beta prior alpha (uniform by default)
            prior_beta: Beta prior beta
        """
        self.arms: Dict[str, BanditArm] = {}
        for arm_id in arm_ids:
            self.arms[arm_id] = BanditArm(
                arm_id=arm_id,
                successes=int(prior_alpha),
                failures=int(prior_beta),
                total_pulls=0,
                estimated_value=prior_alpha / (prior_alpha + prior_beta),
                ucb_value=1.0,
            )

    def select_arm(self) -> str:
        """
        Select an arm using Thompson Sampling.

        Returns the arm ID to show to the next user.
        """
        samples = {}
        for arm_id, arm in self.arms.items():
            # Sample from Beta posterior
            sample = np.random.beta(arm.successes, arm.failures)
            samples[arm_id] = sample

        # Return arm with highest sample
        return max(samples, key=samples.get)

    def update(self, arm_id: str, success: bool) -> None:
        """
        Update arm with observation.

        Args:
            arm_id: The arm that was pulled
            success: Whether the pull was successful (conversion)
        """
        if arm_id not in self.arms:
            return

        arm = self.arms[arm_id]
        arm.total_pulls += 1

        if success:
            arm.successes += 1
        else:
            arm.failures += 1

        # Update estimates
        arm.estimated_value = arm.successes / (arm.successes + arm.failures)

        # Update UCB (for reporting)
        total_pulls = sum(a.total_pulls for a in self.arms.values())
        if arm.total_pulls > 0:
            arm.ucb_value = arm.estimated_value + math.sqrt(
                2 * math.log(total_pulls + 1) / arm.total_pulls
            )

    def get_allocation_weights(self) -> Dict[str, float]:
        """
        Get current recommended traffic allocation.

        Returns probability each arm should be shown.
        """
        num_samples = 10000
        selections = {arm_id: 0 for arm_id in self.arms}

        for _ in range(num_samples):
            selected = self.select_arm()
            selections[selected] += 1

        total = sum(selections.values())
        return {arm_id: count / total for arm_id, count in selections.items()}

    def get_results(self) -> Dict[str, Any]:
        """Get current bandit state and recommendations."""
        allocations = self.get_allocation_weights()

        # Find best arm
        best_arm = max(self.arms.values(), key=lambda a: a.estimated_value)

        return {
            "arms": [
                {
                    "arm_id": arm.arm_id,
                    "successes": arm.successes,
                    "failures": arm.failures,
                    "total_pulls": arm.total_pulls,
                    "conversion_rate": round(arm.estimated_value, 4),
                    "traffic_allocation": round(allocations[arm.arm_id], 4),
                }
                for arm in self.arms.values()
            ],
            "best_arm": best_arm.arm_id,
            "best_conversion_rate": round(best_arm.estimated_value, 4),
            "total_observations": sum(a.total_pulls for a in self.arms.values()),
        }


# Singleton instances
bayesian_tester = BayesianABTester()
cuped_analyzer = CUPEDAnalyzer()
