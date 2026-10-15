//! Distance-based rotary encoder emulation for touchpad edge gestures.
//!
//! Converts continuous finger movement along a touchpad edge into discrete
//! keyboard event ticks. Distance traveled determines the number of discrete
//! key presses, behaving like a rotary encoder hardware knob rather than a
//! one-shot swipe.

use std::time::Duration;
use crate::core::{AxisRange, SliderDirection, Zone};

pub const DEFAULT_ENCODER_STEP_SIZE: f32 = 50.0;
pub const DEFAULT_ENCODER_DEAD_ZONE: f32 = 10.0;
pub const DEFAULT_ENCODER_REPEAT_INTERVAL_MS: u64 = 20;

pub const MIN_ENCODER_STEP_SIZE: f32 = 5.0;
pub const MAX_ENCODER_STEP_SIZE: f32 = 500.0;
pub const MIN_ENCODER_DEAD_ZONE: f32 = 0.0;
pub const MAX_ENCODER_DEAD_ZONE: f32 = 100.0;
pub const MIN_ENCODER_REPEAT_INTERVAL_MS: u64 = 5;
pub const MAX_ENCODER_REPEAT_INTERVAL_MS: u64 = 200;

/// Configuration options for distance-based rotary encoder mode.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct EncoderConfig {
    pub enabled: bool,
    /// Movement in raw coordinate units (if >= 1.0) or fraction of axis (if < 1.0) per tick.
    pub step_size: f32,
    /// Minimum initial movement required before ticks start accumulating (dead zone / jitter filter).
    pub dead_zone: f32,
    /// Repeat interval between emitted key press events.
    pub repeat_interval: Duration,
}

impl Default for EncoderConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            step_size: DEFAULT_ENCODER_STEP_SIZE,
            dead_zone: DEFAULT_ENCODER_DEAD_ZONE,
            repeat_interval: Duration::from_millis(DEFAULT_ENCODER_REPEAT_INTERVAL_MS),
        }
    }
}

impl EncoderConfig {
    pub fn sanitize(&mut self) {
        if !self.step_size.is_finite() || self.step_size < MIN_ENCODER_STEP_SIZE {
            self.step_size = DEFAULT_ENCODER_STEP_SIZE;
        } else if self.step_size > MAX_ENCODER_STEP_SIZE {
            self.step_size = MAX_ENCODER_STEP_SIZE;
        }

        if !self.dead_zone.is_finite() || self.dead_zone < MIN_ENCODER_DEAD_ZONE {
            self.dead_zone = 0.0;
        } else if self.dead_zone > MAX_ENCODER_DEAD_ZONE {
            self.dead_zone = MAX_ENCODER_DEAD_ZONE;
        }

        let millis = self.repeat_interval.as_millis() as u64;
        let clamped = millis.clamp(MIN_ENCODER_REPEAT_INTERVAL_MS, MAX_ENCODER_REPEAT_INTERVAL_MS);
        self.repeat_interval = Duration::from_millis(clamped);
    }

    /// Resolve effective step size in coordinate units against the given axis range.
    pub fn effective_step_size(&self, axis: AxisRange) -> f32 {
        if self.step_size < 1.0 {
            let span = (axis.max - axis.min).max(1) as f32;
            (self.step_size * span).max(MIN_ENCODER_STEP_SIZE)
        } else {
            self.step_size
        }
    }

    /// Resolve effective dead zone in coordinate units against the given axis range.
    pub fn effective_dead_zone(&self, axis: AxisRange) -> f32 {
        if self.dead_zone < 1.0 && self.dead_zone > 0.0 {
            let span = (axis.max - axis.min).max(1) as f32;
            self.dead_zone * span
        } else {
            self.dead_zone
        }
    }
}

/// A discrete tick emitted by the encoder accumulator.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct EncoderTick {
    pub zone: Zone,
    pub direction: SliderDirection,
    pub slot: i32,
    pub tracking_id: i32,
}

/// Diagnostic snapshot of the accumulator's active state.
#[derive(Debug, Clone, Copy, PartialEq, Default)]
pub struct EncoderStats {
    pub active: bool,
    pub direction: Option<SliderDirection>,
    pub accumulated_distance: f32,
    pub total_travel: f32,
    pub tick_count: usize,
}

/// Accumulator tracking continuous finger displacement along an edge.
///
/// Preserves fractional remainders across events, rejects sensor jitter,
/// handles direction reversals without lost or duplicate movement, and emits
/// discrete ticks once each step size increment is crossed.
#[derive(Debug, Clone)]
pub struct EncoderAccumulator {
    config: EncoderConfig,
    y_range: AxisRange,
    zone: Zone,
    slot: i32,
    tracking_id: i32,
    active: bool,
    start_y: Option<f32>,
    last_y: Option<f32>,
    dead_zone_passed: bool,
    /// Signed remainder in coordinate units: positive = UP, negative = DOWN.
    remainder: f32,
    total_travel: f32,
    total_ticks: usize,
    last_direction: Option<SliderDirection>,
}

impl EncoderAccumulator {
    pub fn new(config: EncoderConfig, y_range: AxisRange) -> Self {
        Self {
            config,
            y_range,
            zone: Zone::Right,
            slot: 0,
            tracking_id: 0,
            active: false,
            start_y: None,
            last_y: None,
            dead_zone_passed: false,
            remainder: 0.0,
            total_travel: 0.0,
            total_ticks: 0,
            last_direction: None,
        }
    }

    pub fn start_contact(&mut self, zone: Zone, slot: i32, tracking_id: i32, y: i32) {
        self.zone = zone;
        self.slot = slot;
        self.tracking_id = tracking_id;
        self.active = true;
        self.start_y = Some(y as f32);
        self.last_y = Some(y as f32);
        self.dead_zone_passed = false;
        self.remainder = 0.0;
        self.total_travel = 0.0;
        self.total_ticks = 0;
        self.last_direction = None;
    }

    /// Process a new vertical coordinate event.
    ///
    /// Returns a list of discrete ticks generated during this movement increment.
    pub fn update(&mut self, y: i32) -> Vec<EncoderTick> {
        if !self.active || !self.config.enabled {
            return Vec::new();
        }

        let Some(last) = self.last_y else {
            // First event: establishes initial touch point.
            // Never counts initial finger-down as a movement tick.
            self.start_y = Some(y as f32);
            self.last_y = Some(y as f32);
            return Vec::new();
        };

        let current_y = y as f32;
        // In Linux touchpads, Y increases downwards (0 = top, max = bottom).
        // Decreasing Y means moving UP; increasing Y means moving DOWN.
        // Therefore, (last - current_y) is POSITIVE when moving UP, and NEGATIVE when moving DOWN.
        let raw_delta = last - current_y;

        // Ignore stationary events (zero delta).
        if raw_delta == 0.0 {
            return Vec::new();
        }

        let dead_zone = self.config.effective_dead_zone(self.y_range);
        let step_size = self.config.effective_step_size(self.y_range);

        // Check if dead zone has been crossed from the initial contact point.
        if !self.dead_zone_passed {
            let start = self.start_y.unwrap_or(last);
            let total_disp_from_start = (start - current_y).abs();
            if total_disp_from_start < dead_zone {
                // Still inside dead zone: ignore sensor jitter.
                self.last_y = Some(current_y);
                return Vec::new();
            }
            self.dead_zone_passed = true;
        }

        self.last_y = Some(current_y);
        self.total_travel += raw_delta.abs();
        self.remainder += raw_delta;

        let mut ticks = Vec::new();

        // Moving UP: remainder >= step_size
        while self.remainder >= step_size {
            self.remainder -= step_size;
            self.total_ticks += 1;
            self.last_direction = Some(SliderDirection::Up);
            ticks.push(EncoderTick {
                zone: self.zone,
                direction: SliderDirection::Up,
                slot: self.slot,
                tracking_id: self.tracking_id,
            });
        }

        // Moving DOWN: remainder <= -step_size
        while self.remainder <= -step_size {
            self.remainder += step_size;
            self.total_ticks += 1;
            self.last_direction = Some(SliderDirection::Down);
            ticks.push(EncoderTick {
                zone: self.zone,
                direction: SliderDirection::Down,
                slot: self.slot,
                tracking_id: self.tracking_id,
            });
        }

        ticks
    }

    /// Reset accumulator state when a touch contact ends.
    pub fn reset(&mut self) {
        self.active = false;
        self.start_y = None;
        self.last_y = None;
        self.dead_zone_passed = false;
        self.remainder = 0.0;
        self.total_travel = 0.0;
        self.total_ticks = 0;
        self.last_direction = None;
    }

    pub fn is_active(&self) -> bool {
        self.active
    }

    pub fn total_ticks(&self) -> usize {
        self.total_ticks
    }

    pub fn total_travel(&self) -> f32 {
        self.total_travel
    }

    pub fn remainder(&self) -> f32 {
        self.remainder
    }

    pub fn stats(&self) -> EncoderStats {
        EncoderStats {
            active: self.active,
            direction: self.last_direction,
            accumulated_distance: self.remainder.abs(),
            total_travel: self.total_travel,
            tick_count: self.total_ticks,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_range() -> AxisRange {
        AxisRange { min: 0, max: 1766 }
    }

    fn test_config(step_size: f32, dead_zone: f32) -> EncoderConfig {
        EncoderConfig {
            enabled: true,
            step_size,
            dead_zone,
            repeat_interval: Duration::from_millis(20),
        }
    }

    #[test]
    fn one_complete_step_generates_one_tick() {
        let mut acc = EncoderAccumulator::new(test_config(50.0, 0.0), test_range());
        acc.start_contact(Zone::Right, 0, 1, 1000);

        // Move up 50 units (1000 -> 950)
        let ticks = acc.update(950);
        assert_eq!(ticks.len(), 1);
        assert_eq!(ticks[0].direction, SliderDirection::Up);
        assert_eq!(acc.remainder(), 0.0);
    }

    #[test]
    fn three_complete_steps_generate_three_ticks() {
        let mut acc = EncoderAccumulator::new(test_config(50.0, 0.0), test_range());
        acc.start_contact(Zone::Right, 0, 1, 1000);

        // Move up 150 units in one delta (1000 -> 850)
        let ticks = acc.update(850);
        assert_eq!(ticks.len(), 3);
        assert!(ticks.iter().all(|t| t.direction == SliderDirection::Up));
        assert_eq!(acc.remainder(), 0.0);
    }

    #[test]
    fn partial_movement_accumulates_correctly_across_events() {
        let mut acc = EncoderAccumulator::new(test_config(50.0, 0.0), test_range());
        acc.start_contact(Zone::Right, 0, 1, 1000);

        // Move up 25 units: 0 ticks, remainder 25
        assert_eq!(acc.update(975).len(), 0);
        assert_eq!(acc.remainder(), 25.0);

        // Move up another 25 units: 1 tick, remainder 0
        let ticks = acc.update(950);
        assert_eq!(ticks.len(), 1);
        assert_eq!(ticks[0].direction, SliderDirection::Up);
        assert_eq!(acc.remainder(), 0.0);
    }

    #[test]
    fn displacement_175_units_with_50_step_produces_three_ticks() {
        // Illustrative table from specification:
        // 25 units -> 0
        // 50 units -> 1
        // 100 units -> 2
        // 175 units -> 3
        // 300 units -> 6
        let mut acc = EncoderAccumulator::new(test_config(50.0, 0.0), test_range());
        acc.start_contact(Zone::Right, 0, 1, 1000);

        // 25 units -> 0
        assert_eq!(acc.update(975).len(), 0);
        assert_eq!(acc.total_ticks(), 0);

        // 50 units total (another 25) -> 1 tick
        assert_eq!(acc.update(950).len(), 1);
        assert_eq!(acc.total_ticks(), 1);

        // 100 units total (another 50) -> 1 tick (total 2)
        assert_eq!(acc.update(900).len(), 1);
        assert_eq!(acc.total_ticks(), 2);

        // 175 units total (another 75) -> 1 tick (total 3), remainder 25
        assert_eq!(acc.update(825).len(), 1);
        assert_eq!(acc.total_ticks(), 3);
        assert_eq!(acc.remainder(), 25.0);

        // 300 units total (another 125) -> 125 + 25 = 150 = 3 ticks (total 6)
        assert_eq!(acc.update(700).len(), 3);
        assert_eq!(acc.total_ticks(), 6);
        assert_eq!(acc.remainder(), 0.0);
    }

    #[test]
    fn small_jitter_does_not_generate_unwanted_ticks() {
        let mut acc = EncoderAccumulator::new(test_config(50.0, 10.0), test_range());
        acc.start_contact(Zone::Right, 0, 1, 1000);

        // Jitter within dead zone (+/- 3 units)
        assert_eq!(acc.update(1002).len(), 0);
        assert_eq!(acc.update(998).len(), 0);
        assert_eq!(acc.update(1001).len(), 0);
        assert_eq!(acc.update(1000).len(), 0);
        assert_eq!(acc.total_ticks(), 0);
    }

    #[test]
    fn reversing_direction_does_not_duplicate_or_lose_movement() {
        let mut acc = EncoderAccumulator::new(test_config(50.0, 0.0), test_range());
        acc.start_contact(Zone::Right, 0, 1, 1000);

        // Move UP 75 units -> 1 Up tick, remainder +25
        let ticks_up = acc.update(925);
        assert_eq!(ticks_up.len(), 1);
        assert_eq!(ticks_up[0].direction, SliderDirection::Up);
        assert_eq!(acc.remainder(), 25.0);

        // Reverse: Move DOWN 30 units -> remainder shifts from +25 to -5
        let ticks_rev1 = acc.update(955);
        assert_eq!(ticks_rev1.len(), 0);
        assert_eq!(acc.remainder(), -5.0);

        // Continue DOWN another 45 units -> remainder reaches -50 -> 1 Down tick!
        let ticks_rev2 = acc.update(1000);
        assert_eq!(ticks_rev2.len(), 1);
        assert_eq!(ticks_rev2[0].direction, SliderDirection::Down);
        assert_eq!(acc.remainder(), 0.0);
    }

    #[test]
    fn touch_end_resets_gesture_local_state() {
        let mut acc = EncoderAccumulator::new(test_config(50.0, 0.0), test_range());
        acc.start_contact(Zone::Right, 0, 1, 1000);
        acc.update(960); // 40 units remainder
        assert_eq!(acc.remainder(), 40.0);

        acc.reset();
        assert!(!acc.is_active());
        assert_eq!(acc.remainder(), 0.0);
        assert_eq!(acc.total_ticks(), 0);
    }

    #[test]
    fn new_gesture_starts_with_clean_accumulator() {
        let mut acc = EncoderAccumulator::new(test_config(50.0, 0.0), test_range());
        acc.start_contact(Zone::Right, 0, 1, 1000);
        acc.update(900); // 100 units -> 2 ticks
        assert_eq!(acc.total_ticks(), 2);
        acc.reset();

        // Start second gesture
        acc.start_contact(Zone::Right, 0, 2, 500);
        assert_eq!(acc.total_ticks(), 0);
        assert_eq!(acc.remainder(), 0.0);

        // Move 25 units: no ticks
        assert_eq!(acc.update(475).len(), 0);
        // Move another 25 units: 1 tick
        assert_eq!(acc.update(450).len(), 1);
        assert_eq!(acc.total_ticks(), 1);
    }

    #[test]
    fn downward_swipes_generate_down_ticks() {
        let mut acc = EncoderAccumulator::new(test_config(50.0, 0.0), test_range());
        acc.start_contact(Zone::Left, 0, 1, 500);

        // Y increases going down: 500 -> 550 (+50 down)
        let ticks = acc.update(550);
        assert_eq!(ticks.len(), 1);
        assert_eq!(ticks[0].direction, SliderDirection::Down);
        assert_eq!(ticks[0].zone, Zone::Left);
    }

    #[test]
    fn normalized_step_size_calculates_against_axis_range() {
        let range = AxisRange { min: 0, max: 2000 };
        // 0.05 normalized of 2000 is 100 units
        let config = test_config(0.05, 0.0);
        assert_eq!(config.effective_step_size(range), 100.0);

        let mut acc = EncoderAccumulator::new(config, range);
        acc.start_contact(Zone::Right, 0, 1, 1000);
        assert_eq!(acc.update(950).len(), 0); // 50 units: 0 ticks
        assert_eq!(acc.update(900).len(), 1); // 100 units: 1 tick
    }

    #[test]
    fn engine_encoder_long_swipe_generates_multiple_slider_steps() {
        use crate::core::{Capabilities, EdgeWidths, Engine, EngineOptions, Event};

        let caps = Capabilities {
            slot_min: 0,
            slot_max: 9,
            x: AxisRange { min: 0, max: 1000 },
            y: AxisRange { min: 0, max: 1000 },
        };
        let mut options = EngineOptions::default();
        options.encoder.enabled = true;
        options.encoder.step_size = 50.0;
        options.encoder.dead_zone = 10.0;

        let mut engine = Engine::with_options(caps, EdgeWidths::all(0.10), Vec::new(), options);

        // Frame 1: Finger down on right edge (x=950, y=1000)
        let f1 = vec![
            Event::slot(0),
            Event::tracking_id(10),
            Event::x(950),
            Event::y(1000),
        ];
        let out1 = engine.process_frame(&f1).expect("frame 1 should succeed");
        assert_eq!(out1.slider_steps.len(), 0);

        // Frame 2: Move by 25 units (y=975) -> 0 ticks
        let f2 = vec![Event::slot(0), Event::y(975)];
        let out2 = engine.process_frame(&f2).expect("frame 2 should succeed");
        assert_eq!(out2.slider_steps.len(), 0);

        // Frame 3: Move another 25 units (y=950, total 50 units) -> 1 tick
        let f3 = vec![Event::slot(0), Event::y(950)];
        let out3 = engine.process_frame(&f3).expect("frame 3 should succeed");
        assert_eq!(out3.slider_steps.len(), 1);
        assert_eq!(out3.slider_steps[0].direction, SliderDirection::Up);
        assert_eq!(out3.slider_steps[0].zone, Zone::Right);

        // Frame 4: Move to y=825 (total 175 units from start) -> 2 more ticks (total 3 ticks)
        let f4 = vec![Event::slot(0), Event::y(825)];
        let out4 = engine.process_frame(&f4).expect("frame 4 should succeed");
        assert_eq!(out4.slider_steps.len(), 2);
        assert_eq!(out4.slider_steps[0].direction, SliderDirection::Up);
        assert_eq!(out4.slider_steps[1].direction, SliderDirection::Up);

        // Frame 5: Finger lift -> no duplicate gesture should be emitted
        let f5 = vec![Event::slot(0), Event::tracking_id(-1)];
        let out5 = engine.process_frame(&f5).expect("frame 5 should succeed");
        assert_eq!(out5.slider_steps.len(), 0);
        assert_eq!(out5.gestures.len(), 0);
    }

    #[test]
    fn engine_encoder_direction_reversal_in_same_gesture() {
        use crate::core::{Capabilities, EdgeWidths, Engine, EngineOptions, Event};

        let caps = Capabilities {
            slot_min: 0,
            slot_max: 9,
            x: AxisRange { min: 0, max: 1000 },
            y: AxisRange { min: 0, max: 1000 },
        };
        let mut options = EngineOptions::default();
        options.encoder.enabled = true;
        options.encoder.step_size = 50.0;
        options.encoder.dead_zone = 0.0;

        let mut engine = Engine::with_options(caps, EdgeWidths::all(0.10), Vec::new(), options);

        // Contact starts on left edge at y=500
        let f1 = vec![
            Event::slot(0),
            Event::tracking_id(20),
            Event::x(50),
            Event::y(500),
        ];
        engine.process_frame(&f1).unwrap();

        // Swipe UP to y=400 (100 units up) -> 2 Up ticks
        let f2 = vec![Event::slot(0), Event::y(400)];
        let out2 = engine.process_frame(&f2).unwrap();
        assert_eq!(out2.slider_steps.len(), 2);
        assert_eq!(out2.slider_steps[0].direction, SliderDirection::Up);
        assert_eq!(out2.slider_steps[1].direction, SliderDirection::Up);

        // Reverse DOWN to y=450 (50 units down) -> 1 Down tick
        let f3 = vec![Event::slot(0), Event::y(450)];
        let out3 = engine.process_frame(&f3).unwrap();
        assert_eq!(out3.slider_steps.len(), 1);
        assert_eq!(out3.slider_steps[0].direction, SliderDirection::Down);
        assert_eq!(out3.slider_steps[0].zone, Zone::Left);
    }

    #[test]
    fn engine_encoder_does_not_interfere_with_center_touch_passthrough() {
        use crate::core::{Capabilities, EdgeWidths, Engine, EngineOptions, Event};

        let caps = Capabilities {
            slot_min: 0,
            slot_max: 9,
            x: AxisRange { min: 0, max: 1000 },
            y: AxisRange { min: 0, max: 1000 },
        };
        let mut options = EngineOptions::default();
        options.encoder.enabled = true;

        let mut engine = Engine::with_options(caps, EdgeWidths::all(0.10), Vec::new(), options);

        // Center touch (x=500, y=500)
        let f1 = vec![
            Event::slot(0),
            Event::tracking_id(30),
            Event::x(500),
            Event::y(500),
        ];
        let out1 = engine.process_frame(&f1).unwrap();
        assert!(out1.slider_steps.is_empty());
        assert!(!out1.passthrough.is_empty());

        // Move in center
        let f2 = vec![Event::slot(0), Event::x(510), Event::y(520)];
        let out2 = engine.process_frame(&f2).unwrap();
        assert!(out2.slider_steps.is_empty());
        assert!(!out2.passthrough.is_empty());
    }
}
