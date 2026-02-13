import unittest
from datetime import datetime, timedelta, timezone
import tempfile
import os
import threading
import time
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import base_types as entropy_types
import calculator
import monitor
import sweeper
import attribution
import adaptive_threshold
import persistence
import engine

EntropyLevel = entropy_types.EntropyLevel
EntropyCategory = entropy_types.EntropyCategory
AlertSeverity = entropy_types.AlertSeverity
SweepPriority = entropy_types.SweepPriority
SweepStatus = entropy_types.SweepStatus
EntropyThreshold = entropy_types.EntropyThreshold
EntropySample = entropy_types.EntropySample
EntropyAlert = entropy_types.EntropyAlert
SweepAction = entropy_types.SweepAction
TrendAnalysis = entropy_types.TrendAnalysis
AttributionResult = entropy_types.AttributionResult
AdaptiveThreshold = entropy_types.AdaptiveThreshold
utc_now = entropy_types.utc_now
EntropyCalculator = calculator.EntropyCalculator
MetricDefinition = calculator.MetricDefinition
exponential_decay = calculator.exponential_decay
weighted_entropy = calculator.weighted_entropy
EntropyMonitor = monitor.EntropyMonitor
AlertRule = monitor.AlertRule
EntropySweeper = sweeper.EntropySweeper
SweepStrategy = sweeper.SweepStrategy
EntropyAttributor = attribution.EntropyAttributor
AdaptiveThresholdManager = adaptive_threshold.AdaptiveThresholdManager
EntropyPersistence = persistence.EntropyPersistence
EntropyEngine = engine.EntropyEngine
EntropyEngineConfig = engine.EntropyEngineConfig


class TestTypes(unittest.TestCase):
    def test_entropy_threshold_classify(self):
        threshold = EntropyThreshold(
            category=EntropyCategory.EVOLUTION,
            warning=0.3, critical=0.6, emergency=0.8
        )
        self.assertEqual(threshold.classify(0.1), AlertSeverity.INFO)
        self.assertEqual(threshold.classify(0.4), AlertSeverity.WARNING)
        self.assertEqual(threshold.classify(0.7), AlertSeverity.CRITICAL)
        self.assertEqual(threshold.classify(0.9), AlertSeverity.EMERGENCY)

    def test_entropy_sample_creation(self):
        sample = EntropySample(
            timestamp=utc_now(),
            category=EntropyCategory.INPUT,
            level=EntropyLevel.SYSTEM,
            source="test_source",
            value=0.5,
            raw_metrics={"count": 10},
            tags={"env": "test"},
        )
        self.assertEqual(sample.category, EntropyCategory.INPUT)
        self.assertEqual(sample.level, EntropyLevel.SYSTEM)
        self.assertEqual(sample.value, 0.5)

    def test_sweep_action_status(self):
        action = SweepAction(
            action_id="test-1",
            name="Test Action",
            description="Test",
            priority=SweepPriority.HIGH,
            category=EntropyCategory.EVOLUTION,
            source="test",
            estimated_impact=0.5,
        )
        self.assertEqual(action.status, SweepStatus.PENDING)


class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calculator = EntropyCalculator()

    def test_register_metric(self):
        metric = MetricDefinition(
            name="custom_metric",
            category=EntropyCategory.BEHAVIOR,
            level=EntropyLevel.COMPONENT,
            weight=1.5,
        )
        self.calculator.register_metric(metric)
        sample = self.calculator.record_sample(
            "custom_metric", 0.5, "test_source"
        )
        self.assertIsNotNone(sample)
        self.assertEqual(sample.category, EntropyCategory.BEHAVIOR)

    def test_record_sample(self):
        sample = self.calculator.record_sample(
            "inbox_stale", 0.3, "inbox"
        )
        self.assertIsNotNone(sample)
        entropy = self.calculator.compute_entropy()
        self.assertGreaterEqual(entropy, 0.0)

    def test_compute_by_category(self):
        for i in range(10):
            self.calculator.record_sample(
                "inbox_stale", 0.2 + i * 0.02, "inbox"
            )
        by_category = self.calculator.compute_by_category()
        self.assertIn(EntropyCategory.INPUT, by_category)
        self.assertGreater(by_category[EntropyCategory.INPUT], 0)

    def test_compute_by_level(self):
        self.calculator.record_sample("inbox_stale", 0.3, "test")
        by_level = self.calculator.compute_by_level()
        self.assertIn(EntropyLevel.SYSTEM, by_level)

    def test_compute_health_score(self):
        for i in range(5):
            self.calculator.record_sample("error_rate", 0.1, "source")
        score = self.calculator.compute_health_score()
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_get_top_contributors(self):
        self.calculator.record_sample("inbox_stale", 0.8, "source_a")
        self.calculator.record_sample("inbox_stale", 0.3, "source_b")
        contributors = self.calculator.get_top_contributors(top_n=2)
        self.assertEqual(len(contributors), 2)
        self.assertEqual(contributors[0].source, "source_a")


class TestMonitor(unittest.TestCase):
    def setUp(self):
        self.calculator = EntropyCalculator()
        self.monitor = EntropyMonitor(self.calculator)

    def test_check_and_alert(self):
        for i in range(20):
            self.calculator.record_sample(
                "unindexed_outputs", 0.8 + i * 0.01, "test"
            )
        alerts = self.monitor.check_and_alert(category=EntropyCategory.EVOLUTION)
        self.assertIsInstance(alerts, list)

    def test_acknowledge_alert(self):
        alert = EntropyAlert(
            alert_id="test-alert-1",
            timestamp=utc_now(),
            severity=AlertSeverity.WARNING,
            category=EntropyCategory.EVOLUTION,
            source="test",
            current_value=0.5,
            threshold=0.3,
            message="Test alert",
        )
        self.monitor._alerts.append(alert)
        result = self.monitor.acknowledge_alert("test-alert-1", "user")
        self.assertIsNotNone(result)
        self.assertTrue(result.acknowledged)

    def test_analyze_trend_insufficient_samples(self):
        trend = self.monitor.analyze_trend(EntropyCategory.EVOLUTION)
        self.assertIsNone(trend)

    def test_analyze_trend_with_samples(self):
        for i in range(20):
            self.calculator.record_sample(
                "inbox_stale", 0.3 + i * 0.05, "test_source"
            )
        trend = self.monitor.analyze_trend(EntropyCategory.INPUT)
        self.assertIsNotNone(trend)
        self.assertEqual(trend.category, EntropyCategory.INPUT)
        self.assertIn(trend.trend_direction, ["increasing", "stable"])

    def test_generate_report(self):
        for i in range(10):
            self.calculator.record_sample("error_rate", 0.2, "test")
        report = self.monitor.generate_report()
        self.assertIsNotNone(report.timestamp)
        self.assertIsInstance(report.total_entropy, float)
        self.assertIsInstance(report.health_score, float)
        self.assertIsInstance(report.recommendations, list)


class TestSweeper(unittest.TestCase):
    def setUp(self):
        self.calculator = EntropyCalculator()
        self.monitor = EntropyMonitor(self.calculator)
        self.sweeper = EntropySweeper(self.calculator, self.monitor)

    def test_register_strategy(self):
        strategy = SweepStrategy(
            strategy_id="test_strategy",
            name="Test Strategy",
            category=EntropyCategory.EVOLUTION,
            priority=SweepPriority.MEDIUM,
            condition=lambda e: e > 0.5,
            action_generator=lambda: [],
        )
        self.sweeper.register_strategy(strategy)
        self.assertIn("test_strategy", self.sweeper._strategies)

    def test_prioritize_actions(self):
        actions = [
            SweepAction(
                action_id="a1", name="A1", description="",
                priority=SweepPriority.LOW, category=EntropyCategory.EVOLUTION,
                source="s1", estimated_impact=0.3
            ),
            SweepAction(
                action_id="a2", name="A2", description="",
                priority=SweepPriority.HIGH, category=EntropyCategory.EVOLUTION,
                source="s2", estimated_impact=0.5
            ),
            SweepAction(
                action_id="a3", name="A3", description="",
                priority=SweepPriority.CRITICAL, category=EntropyCategory.EVOLUTION,
                source="s3", estimated_impact=0.8
            ),
        ]
        prioritized = self.sweeper.prioritize_actions(actions)
        self.assertEqual(prioritized[0].action_id, "a3")

    def test_execute_action_dry_run(self):
        action = SweepAction(
            action_id="test-dry", name="Dry Run", description="",
            priority=SweepPriority.MEDIUM, category=EntropyCategory.EVOLUTION,
            source="test", estimated_impact=0.5, executor="default"
        )
        result = self.sweeper.execute_action(action, dry_run=True)
        self.assertTrue(result.success)
        self.assertTrue(result.details.get("dry_run", False))

    def test_get_statistics(self):
        stats = self.sweeper.get_statistics()
        self.assertIn("total_actions", stats)
        self.assertIn("pending", stats)


class TestAttribution(unittest.TestCase):
    def setUp(self):
        self.calculator = EntropyCalculator()
        self.attributor = EntropyAttributor(self.calculator)

    def test_analyze_empty(self):
        results = self.attributor.analyze()
        self.assertIsInstance(results, list)

    def test_analyze_with_samples(self):
        for i in range(20):
            self.calculator.record_sample(
                "error_rate", 0.3 + i * 0.02, "source_a"
            )
            self.calculator.record_sample(
                "cache_miss_rate", 0.2 + i * 0.01, "source_b"
            )
        results = self.attributor.analyze(top_n=5)
        self.assertGreater(len(results), 0)

    def test_generate_hypotheses(self):
        for i in range(30):
            self.calculator.record_sample(
                "error_rate", 0.7 + i * 0.01, "high_entropy_source"
            )
        hypotheses = self.attributor.generate_hypotheses()
        self.assertIsInstance(hypotheses, list)


class TestAdaptiveThreshold(unittest.TestCase):
    def setUp(self):
        self.calculator = EntropyCalculator()
        self.manager = AdaptiveThresholdManager(
            self.calculator,
            adaptation_interval_hours=0.01,
            min_samples=5,
        )

    def test_record_baseline(self):
        self.manager.record_baseline(EntropyCategory.EVOLUTION, 0.3)
        self.manager.record_baseline(EntropyCategory.EVOLUTION, 0.35)
        self.assertGreater(len(self.manager._baseline_history[EntropyCategory.EVOLUTION]), 0)

    def test_should_adapt(self):
        for i in range(60):
            self.manager.record_baseline(EntropyCategory.EVOLUTION, 0.3)
        result = self.manager.should_adapt(EntropyCategory.EVOLUTION)
        self.assertTrue(result)

    def test_adapt_threshold(self):
        for i in range(60):
            self.manager.record_baseline(EntropyCategory.EVOLUTION, 0.3 + i * 0.005)
        adjustment = self.manager.adapt_threshold(EntropyCategory.EVOLUTION)
        if adjustment:
            self.assertEqual(adjustment.category, EntropyCategory.EVOLUTION)

    def test_reset_to_baseline(self):
        threshold = self.manager.reset_to_baseline(EntropyCategory.EVOLUTION)
        self.assertIsNotNone(threshold.warning)


class TestPersistence(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.persistence = EntropyPersistence(db_path=self.db_path)

    def tearDown(self):
        self.persistence.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_save_and_load_sample(self):
        sample = EntropySample(
            timestamp=utc_now(),
            category=EntropyCategory.EVOLUTION,
            level=EntropyLevel.MODULE,
            source="test",
            value=0.5,
        )
        self.persistence.save_sample(sample)
        samples = self.persistence.load_samples(source="test")
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].source, "test")

    def test_save_and_load_alert(self):
        alert = EntropyAlert(
            alert_id="test-alert",
            timestamp=utc_now(),
            severity=AlertSeverity.WARNING,
            category=EntropyCategory.EVOLUTION,
            source="test",
            current_value=0.6,
            threshold=0.4,
            message="Test",
        )
        self.persistence.save_alert(alert)
        alerts = self.persistence.load_alerts()
        self.assertEqual(len(alerts), 1)

    def test_save_and_load_threshold(self):
        threshold = EntropyThreshold(
            category=EntropyCategory.EVOLUTION,
            warning=0.3, critical=0.6, emergency=0.8
        )
        self.persistence.save_threshold(threshold)
        loaded = self.persistence.load_thresholds()
        self.assertIn(EntropyCategory.EVOLUTION, loaded)


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.config = EntropyEngineConfig(db_path=self.db_path)
        self.engine = EntropyEngine(self.config)

    def tearDown(self):
        self.engine.stop()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_record(self):
        sample = self.engine.record("inbox_stale", 0.3, "test")
        self.assertIsNotNone(sample)

    def test_get_entropy(self):
        self.engine.record("inbox_stale", 0.3, "test")
        entropy = self.engine.get_entropy()
        self.assertGreaterEqual(entropy, 0.0)

    def test_get_health_score(self):
        self.engine.record("error_rate", 0.2, "test")
        score = self.engine.get_health_score()
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_get_report(self):
        self.engine.record("inbox_stale", 0.3, "test")
        report = self.engine.get_report()
        self.assertIsNotNone(report)

    def test_check_alerts(self):
        alerts = self.engine.check_alerts()
        self.assertIsInstance(alerts, list)

    def test_get_statistics(self):
        stats = self.engine.get_statistics()
        self.assertIn("calculator", stats)
        self.assertIn("monitor", stats)


class TestConcurrency(unittest.TestCase):
    def setUp(self):
        self.calculator = EntropyCalculator()

    def test_concurrent_recording(self):
        threads = []
        errors = []

        def record_samples(thread_id):
            try:
                for i in range(100):
                    self.calculator.record_sample(
                        "inbox_stale", 0.1 + thread_id * 0.01, f"source_{thread_id}"
                    )
            except Exception as e:
                errors.append(e)

        for i in range(10):
            t = threading.Thread(target=record_samples, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        samples = self.calculator.get_samples(limit=10000)
        self.assertEqual(len(samples), 1000)


class TestExponentialDecay(unittest.TestCase):
    def test_no_decay_at_zero(self):
        self.assertAlmostEqual(exponential_decay(0, 24), 1.0)

    def test_half_life(self):
        self.assertAlmostEqual(exponential_decay(24, 24), 0.5, places=2)

    def test_full_decay(self):
        self.assertAlmostEqual(exponential_decay(168, 24), 0.0, places=1)


class TestWeightedEntropy(unittest.TestCase):
    def test_empty_values(self):
        self.assertEqual(weighted_entropy([]), 0.0)

    def test_single_value(self):
        result = weighted_entropy([(0.5, 1.0)])
        self.assertEqual(result, 0.5)

    def test_weighted_average(self):
        result = weighted_entropy([(0.4, 2.0), (0.6, 1.0)])
        expected = (0.4 * 2.0 + 0.6 * 1.0) / 3.0
        self.assertAlmostEqual(result, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
