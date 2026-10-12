#!/usr/bin/env python3
"""Offline tests using the production filter; no ROS/Gazebo runtime claims."""
from array import array
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from scan_self_filter import filter_scan, in_sector, SELF_FILTER_SECTORS
from compare_scan_filter import inspect_pair


def scan(ranges, angle_min=-math.pi, angle_increment=2 * math.pi / 359):
    return SimpleNamespace(
        header=SimpleNamespace(frame_id='laser_link', stamp=SimpleNamespace(sec=12, nanosec=34)),
        angle_min=angle_min, angle_max=angle_min+(len(ranges)-1)*angle_increment,
        angle_increment=angle_increment, time_increment=0.001, scan_time=0.1,
        range_min=0.12, range_max=10.0, ranges=array('f', ranges),
        intensities=array('f', range(len(ranges))))


class FilterTests(unittest.TestCase):
    # 1.用360个模拟雷达测距点，六个遮挡角度，共检查48个自回波样本是否被过滤，同时保留正前方0.504米的点
    def test_measured_cluster_fixture(self):
        # Synthetic fixture constructed from the user's measured cluster indices.
        raw = [2.0] * 360
        for start, end, distance in ((42, 48, .155), (85, 95, .285), (132, 137, .162),
                                     (222, 227, .167), (264, 274, .277), (311, 317, .160)):
            raw[start:end+1] = [distance] * (end-start+1)
        raw[179] = raw[180] = .504
        msg = scan(raw)
        out = filter_scan(msg)
        self.assertEqual(sum(math.isinf(x) for x in out.ranges), 48)
        self.assertEqual(out.ranges[179:181], msg.ranges[179:181])
        self.assertAlmostEqual(out.ranges[179], .504, places=6)
        self.assertEqual(list(msg.ranges), list(array('f', raw)))

    # 2.六个扇区中的远距离测距不能被删除
    def test_far_returns_in_every_sector_survive(self):
        for start, end, limit in SELF_FILTER_SECTORS:
            for distance in (limit+.01, .50, 4.0):
                msg = scan([distance], math.radians((start+end)/2), .02)
                self.assertEqual(filter_scan(msg).ranges, msg.ranges)

    # 3.检查扇区左右边界、距离严格小于阈值的条件，以及扇区外的点
    def test_angle_bounds_and_strict_distance_limit(self):
        # Use Python doubles here to test exact threshold equality, not float32 rounding.
        for start, end, limit in SELF_FILTER_SECTORS:
            for angle in (start, end):
                msg = scan([], math.radians(angle), .02)
                msg.ranges = [limit-.001, limit]
                msg.angle_increment = 0.0
                self.assertEqual(filter_scan(msg).ranges, [math.inf, limit])
            for angle in (start-.01, end+.01):
                msg = scan([.15], math.radians(angle), .02)
                self.assertEqual(filter_scan(msg).ranges, msg.ranges)

    # 4.检查非标准角度范围、角度统一与负角度增量
    def test_nonstandard_resolution_and_positive_angles(self):
        msg = scan([.15]*6, math.radians(400), math.radians(2))
        self.assertTrue(all(math.isinf(x) for x in filter_scan(msg).ranges))
        msg = scan([.15]*6, math.radians(-400), math.radians(-2))
        self.assertTrue(all(math.isinf(x) for x in filter_scan(msg).ranges))

    # 5.检查正负180度边界及跨边界扇区
    def test_pi_seam_and_wrapping_sector(self):
        for angle in (-180, 180, 540, -540):
            msg = scan([.15], math.radians(angle), .02)
            self.assertEqual(filter_scan(msg).ranges, msg.ranges)
        self.assertTrue(in_sector(179, 170, -170))
        self.assertTrue(in_sector(-179, 170, -170))
        self.assertFalse(in_sector(0, 170, -170))

    # 6.检查 NaN、正无穷和负无穷不会被意外修改
    def test_nan_and_infinities_preserved(self):
        msg = scan([math.nan, math.inf, -math.inf], math.radians(45), 0)
        out = filter_scan(msg)
        self.assertTrue(math.isnan(out.ranges[0]))
        self.assertEqual(list(out.ranges[1:]), [math.inf, -math.inf])

    # 7.检查时间戳、frame_id、强度数组和原始输入是否保持完整
    def test_all_metadata_intensities_and_input_preserved(self):
        msg = scan([.15, .6], math.radians(45), .01)
        out = filter_scan(msg)
        self.assertIsNot(out, msg)
        self.assertIsNot(out.header, msg.header)
        for key in vars(msg):
            if key != 'ranges':
                self.assertEqual(getattr(out, key), getattr(msg, key), key)
        self.assertEqual(len(out.ranges), len(msg.ranges))
        self.assertAlmostEqual(msg.ranges[0], .15)

    # 8.检查扇区之外的近距离真实环境测距能否保留
    def test_near_environment_outside_sectors_preserved(self):
        for angle in (0, 20, -20, 65, -65, 110, -110, 160, -160):
            msg = scan([.13], math.radians(angle), .01)
            self.assertEqual(filter_scan(msg).ranges, msg.ranges)

    # 9.检查空扫描，以及角度数据为无效的情况
    def test_empty_scan_and_invalid_angular_metadata(self):
        self.assertEqual(len(filter_scan(scan([])).ranges), 0)
        msg = scan([.15], math.nan, .01)
        self.assertEqual(filter_scan(msg).ranges, msg.ranges)

    # 10.使用合成的原始/过滤消息，检查能否正确识别六个扇区的过滤结果
    def test_runtime_comparison_checks_synthetic_pair(self):
        raw = [2.0]*360
        for index, distance in ((45, .16), (90, .28), (135, .16),
                                (224, .16), (269, .28), (314, .16)):
            raw[index] = distance
        raw[179] = raw[180] = .504
        msg = scan(raw)
        counts, front_raw, front_filtered = inspect_pair(msg, filter_scan(msg))
        self.assertEqual(counts, [1]*6)
        self.assertEqual(front_raw, front_filtered)

    # 11.人为破坏时间戳，验证能否发现
    def test_runtime_comparison_rejects_damaged_metadata(self):
        msg = scan([.504]*360)
        out = filter_scan(msg)
        out.header.stamp.nanosec += 1
        with self.assertRaisesRegex(ValueError, 'Metadata changed'):
            inspect_pair(msg, out)

    # 12.人为删除一个正常远距离点，验证能否发现
    def test_runtime_comparison_rejects_far_return_removed(self):
        msg = scan([.504]*360)
        out = filter_scan(msg)
        out.ranges[224] = math.inf
        with self.assertRaisesRegex(ValueError, 'Unexpected output'):
            inspect_pair(msg, out)

    # 13.人为保留一个本应过滤的近距离点，验证能否发现
    def test_runtime_comparison_rejects_unfiltered_self_echo(self):
        msg = scan([.504]*360)
        msg.ranges[224] = .16
        with self.assertRaisesRegex(ValueError, 'Unexpected output'):
            inspect_pair(msg, msg)


if __name__ == '__main__':
    unittest.main()
