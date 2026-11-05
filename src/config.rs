//! Parse and validate user configuration before it reaches the input loop.
//!
//! Only zones with bindings become active edges. Validation also rejects a
//! slider and directional gesture on the same edge, since both would consume
//! the same movement. Live device selection is separate from TOML parsing.

use std::collections::BTreeSet;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::str::FromStr;
use std::time::Duration;

use serde::{Deserialize, Serialize};

use crate::core::{
    EdgeWidths, EngineOptions, Gesture, GestureDirection, SliderAxis, SliderDirection, SliderSpec,
    Zone, ZoneSet,
};
use crate::device::{
    discover_device_report, format_device_line, touchpad_candidates, DiscoveryReport,
};
use crate::keyboard::{key_code_to_name, parse_key_code};

pub const DEFAULT_EDGE_WIDTH: f32 = 0.10;
pub const DEFAULT_SLIDER_STEP: f32 = 0.04;
pub const DEFAULT_CONFIG_SWIPE_MAX_DRIFT: f32 = 0.0413;
pub use crate::core::{
    DEFAULT_CORNER_HEIGHT, DEFAULT_CORNER_HITBOX, DEFAULT_CORNER_WIDTH,
    DEFAULT_DOUBLE_TAP_MAX_DISTANCE, DEFAULT_DOUBLE_TAP_TIMEOUT_MS, DEFAULT_SWIPE_MAX_DRIFT,
    DEFAULT_SWIPE_MIN_DISTANCE, DEFAULT_TAP_MAX_DURATION_MS, DEFAULT_TAP_MAX_MOVEMENT,
    DEFAULT_TAP_MIN_DURATION_MS, MAX_CORNER_DIMENSION, MIN_CORNER_DIMENSION,
};
pub const MIN_CORNER_HITBOX: f32 = MIN_CORNER_DIMENSION;
pub const MAX_CORNER_HITBOX: f32 = MAX_CORNER_DIMENSION;

/// Physical detection geometry calibration: controls WHERE a touch occurs.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct HitboxConfig {
    pub edge_width: f32,
    pub left_edge_width: Option<f32>,
    pub right_edge_width: Option<f32>,
    pub top_edge_height: Option<f32>,
    pub bottom_edge_height: Option<f32>,
    pub corner_width: f32,
    pub corner_height: f32,
}

impl Default for HitboxConfig {
    fn default() -> Self {
        Self {
            edge_width: DEFAULT_EDGE_WIDTH,
            left_edge_width: None,
            right_edge_width: None,
            top_edge_height: None,
            bottom_edge_height: None,
            corner_width: DEFAULT_CORNER_WIDTH,
            corner_height: DEFAULT_CORNER_HEIGHT,
        }
    }
}

impl HitboxConfig {
    pub fn resolved_edge_widths(&self) -> EdgeWidths {
        EdgeWidths {
            left: self.left_edge_width.unwrap_or(self.edge_width),
            right: self.right_edge_width.unwrap_or(self.edge_width),
            top: self.top_edge_height.unwrap_or(self.edge_width),
            bottom: self.bottom_edge_height.unwrap_or(self.edge_width),
        }
    }

    pub fn resolved_corner_dimensions(&self) -> (f32, f32) {
        (self.corner_width, self.corner_height)
    }
}

/// Gesture recognition and movement behavior calibration: controls HOW touch input is interpreted.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct GestureConfig {
    pub tap_min_duration_ms: u64,
    pub tap_max_duration_ms: u64,
    pub tap_max_movement: f32,
    pub double_tap_timeout_ms: u64,
    pub double_tap_max_distance: f32,
    pub swipe_min_distance: f32,
    pub swipe_max_drift: f32,
    pub cooldown_ms: u64,
}

impl Default for GestureConfig {
    fn default() -> Self {
        Self {
            tap_min_duration_ms: DEFAULT_TAP_MIN_DURATION_MS,
            tap_max_duration_ms: DEFAULT_TAP_MAX_DURATION_MS,
            tap_max_movement: DEFAULT_TAP_MAX_MOVEMENT,
            double_tap_timeout_ms: DEFAULT_DOUBLE_TAP_TIMEOUT_MS,
            double_tap_max_distance: DEFAULT_DOUBLE_TAP_MAX_DISTANCE,
            swipe_min_distance: DEFAULT_SWIPE_MIN_DISTANCE,
            swipe_max_drift: DEFAULT_CONFIG_SWIPE_MAX_DRIFT,
            cooldown_ms: 250,
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct EdgepadConfig {
    pub device: DeviceConfig,
    pub hitbox: HitboxConfig,
    pub gesture: GestureConfig,
    // Mirrored fields for direct field access and backward compatibility:
    pub edge_width: f32,
    pub edge_width_overrides: EdgeWidthOverrides,
    pub tap_min_duration_ms: u64,
    pub tap_max_duration_ms: u64,
    pub tap_max_movement: f32,
    pub double_tap_timeout_ms: u64,
    pub double_tap_max_distance: f32,
    pub swipe_min_distance: f32,
    pub swipe_max_drift: f32,
    pub corner_hitbox: f32,
    pub corner_width: f32,
    pub corner_height: f32,
    pub encoder: crate::encoder::EncoderConfig,
    pub gestures: Vec<GestureBindingConfig>,
    pub sliders: Vec<SliderBindingConfig>,
}

#[derive(Debug, Clone, Copy, Default, PartialEq)]
pub struct EdgeWidthOverrides {
    pub left: Option<f32>,
    pub right: Option<f32>,
    pub top: Option<f32>,
    pub bottom: Option<f32>,
}

impl Default for EdgepadConfig {
    fn default() -> Self {
        let hitbox = HitboxConfig::default();
        let gesture = GestureConfig::default();
        Self {
            device: DeviceConfig::Auto,
            edge_width: hitbox.edge_width,
            edge_width_overrides: EdgeWidthOverrides::default(),
            tap_min_duration_ms: gesture.tap_min_duration_ms,
            tap_max_duration_ms: gesture.tap_max_duration_ms,
            tap_max_movement: gesture.tap_max_movement,
            double_tap_timeout_ms: gesture.double_tap_timeout_ms,
            double_tap_max_distance: gesture.double_tap_max_distance,
            swipe_min_distance: gesture.swipe_min_distance,
            swipe_max_drift: gesture.swipe_max_drift,
            corner_hitbox: hitbox.corner_width,
            corner_width: hitbox.corner_width,
            corner_height: hitbox.corner_height,
            encoder: crate::encoder::EncoderConfig::default(),
            gestures: Vec::new(),
            sliders: Vec::new(),
            hitbox,
            gesture,
        }
    }
}

impl EdgepadConfig {
    pub fn update_hitbox(&mut self, hitbox: HitboxConfig) {
        self.hitbox = hitbox;
        self.edge_width = hitbox.edge_width;
        self.edge_width_overrides = EdgeWidthOverrides {
            left: hitbox.left_edge_width,
            right: hitbox.right_edge_width,
            top: hitbox.top_edge_height,
            bottom: hitbox.bottom_edge_height,
        };
        self.corner_width = hitbox.corner_width;
        self.corner_height = hitbox.corner_height;
        self.corner_hitbox = hitbox.corner_width;
    }

    pub fn update_gesture(&mut self, gesture: GestureConfig) {
        self.gesture = gesture;
        self.tap_min_duration_ms = gesture.tap_min_duration_ms;
        self.tap_max_duration_ms = gesture.tap_max_duration_ms;
        self.tap_max_movement = gesture.tap_max_movement;
        self.double_tap_timeout_ms = gesture.double_tap_timeout_ms;
        self.double_tap_max_distance = gesture.double_tap_max_distance;
        self.swipe_min_distance = gesture.swipe_min_distance;
        self.swipe_max_drift = gesture.swipe_max_drift;
    }

    pub fn sync_from_subsystems(&mut self) {
        self.update_hitbox(self.hitbox);
        self.update_gesture(self.gesture);
    }

    pub fn parse(input: &str) -> Result<Self, String> {
        let raw = toml::from_str::<RawEdgepadConfig>(input)
            .map_err(|err| format!("invalid TOML config: {err}"))?;
        let mut config = Self::default();
        let mut gesture_keys = BTreeSet::new();
        let mut slider_zones = BTreeSet::new();

        if let Some(device) = raw.device {
            config.device = DeviceConfig::parse(&device)
                .map_err(|err| format!("invalid device config: {err}"))?;
        }

        // 1. Independent Hitbox Calibration Deserialization
        let mut hitbox = HitboxConfig::default();
        if let Some(ref hb) = raw.hitbox {
            if let Some(w) = hb.edge_width {
                hitbox.edge_width = validate_edge_width(w, "hitbox.edge_width")?;
            }
            hitbox.left_edge_width =
                validate_optional_edge_width(hb.left_edge_width, "hitbox.left_edge_width")?;
            hitbox.right_edge_width =
                validate_optional_edge_width(hb.right_edge_width, "hitbox.right_edge_width")?;
            hitbox.top_edge_height =
                validate_optional_edge_width(hb.top_edge_height, "hitbox.top_edge_height")?;
            hitbox.bottom_edge_height =
                validate_optional_edge_width(hb.bottom_edge_height, "hitbox.bottom_edge_height")?;
            if let Some(cw) = hb.corner_width.or(hb.corner_hitbox) {
                hitbox.corner_width = validate_corner_hitbox(cw, "hitbox.corner_width")?;
            }
            if let Some(ch) = hb.corner_height.or(hb.corner_hitbox) {
                hitbox.corner_height = validate_corner_hitbox(ch, "hitbox.corner_height")?;
            }
        } else {
            // Backward-compatible legacy hitbox fields
            if let Some(edge_width) = raw.edge_width {
                hitbox.edge_width = validate_edge_width(edge_width, "edge_width")?;
            }
            hitbox.left_edge_width =
                validate_optional_edge_width(raw.left_edge_width, "left_edge_width")?;
            hitbox.right_edge_width =
                validate_optional_edge_width(raw.right_edge_width, "right_edge_width")?;
            hitbox.top_edge_height =
                validate_optional_edge_width(raw.top_edge_width, "top_edge_width")?;
            hitbox.bottom_edge_height =
                validate_optional_edge_width(raw.bottom_edge_width, "bottom_edge_width")?;
            if let Some(corner_hitbox) = raw.corner_hitbox {
                let val = validate_corner_hitbox(corner_hitbox, "corner_hitbox")?;
                hitbox.corner_width = val;
                hitbox.corner_height = val;
            }
        }
        config.update_hitbox(hitbox);

        // 2. Independent Gesture Calibration Deserialization
        let mut gesture = GestureConfig::default();
        if let Some(ref g) = raw.gesture {
            if let Some(tap_min) = g.tap_min_duration_ms {
                gesture.tap_min_duration_ms =
                    validate_tap_min_duration_ms(tap_min, "gesture.tap_min_duration_ms")?;
            }
            if let Some(tap_max) = g.tap_max_duration_ms {
                gesture.tap_max_duration_ms =
                    validate_tap_max_duration_ms(tap_max, "gesture.tap_max_duration_ms")?;
            }
            if let Some(tap_mov) = g.tap_max_movement {
                gesture.tap_max_movement =
                    validate_tap_max_movement(tap_mov, "gesture.tap_max_movement")?;
            }
            if let Some(dt_timeout) = g.double_tap_timeout_ms {
                gesture.double_tap_timeout_ms =
                    validate_double_tap_timeout_ms(dt_timeout, "gesture.double_tap_timeout_ms")?;
            }
            if let Some(dt_dist) = g.double_tap_max_distance {
                gesture.double_tap_max_distance =
                    validate_double_tap_max_distance(dt_dist, "gesture.double_tap_max_distance")?;
            }
            if let Some(swipe_dist) = g.swipe_min_distance {
                gesture.swipe_min_distance =
                    validate_swipe_min_distance(swipe_dist, "gesture.swipe_min_distance")?;
            }
            if let Some(swipe_drift) = g.swipe_max_drift {
                gesture.swipe_max_drift =
                    validate_swipe_max_drift(swipe_drift, "gesture.swipe_max_drift")?;
            }
            if let Some(cooldown) = g.cooldown_ms {
                gesture.cooldown_ms = cooldown;
            }
        } else {
            // Backward-compatible legacy gesture fields
            if let Some(tap_min_duration_ms) = raw.tap_min_duration_ms {
                gesture.tap_min_duration_ms =
                    validate_tap_min_duration_ms(tap_min_duration_ms, "tap_min_duration_ms")?;
            }
            if let Some(tap_max_duration_ms) = raw.tap_max_duration_ms {
                gesture.tap_max_duration_ms =
                    validate_tap_max_duration_ms(tap_max_duration_ms, "tap_max_duration_ms")?;
            } else if let Some(ref engine) = raw.engine {
                if let Some(tap_max_dur) = engine.tap_max_duration_ms {
                    gesture.tap_max_duration_ms =
                        validate_tap_max_duration_ms(tap_max_dur, "engine.tap_max_duration_ms")?;
                }
            }
            if let Some(double_tap_timeout_ms) = raw.double_tap_timeout_ms {
                gesture.double_tap_timeout_ms =
                    validate_double_tap_timeout_ms(double_tap_timeout_ms, "double_tap_timeout_ms")?;
            }
            if let Some(double_tap_max_distance) = raw.double_tap_max_distance {
                gesture.double_tap_max_distance = validate_double_tap_max_distance(
                    double_tap_max_distance,
                    "double_tap_max_distance",
                )?;
            }
            if let Some(swipe_min_distance) = raw.swipe_min_distance {
                gesture.swipe_min_distance =
                    validate_swipe_min_distance(swipe_min_distance, "swipe_min_distance")?;
            } else if let Some(ref engine) = raw.engine {
                if let Some(min_travel) = engine.min_travel {
                    let dist_frac = if min_travel > 1.0 {
                        min_travel / 2905.0
                    } else {
                        min_travel
                    };
                    gesture.swipe_min_distance =
                        validate_swipe_min_distance(dist_frac, "engine.min_travel")?;
                }
            }
            if let Some(swipe_max_drift) = raw.swipe_max_drift {
                gesture.swipe_max_drift =
                    validate_swipe_max_drift(swipe_max_drift, "swipe_max_drift")?;
            } else if let Some(ref engine) = raw.engine {
                if let Some(max_drift) = engine.max_drift {
                    let drift_frac = if max_drift > 1.0 {
                        max_drift / 2905.0
                    } else {
                        max_drift
                    };
                    gesture.swipe_max_drift =
                        validate_swipe_max_drift(drift_frac, "engine.max_drift")?;
                }
            }
            if let Some(ref engine) = raw.engine {
                if let Some(cooldown) = engine.cooldown_ms {
                    gesture.cooldown_ms = cooldown;
                }
                if let Some(tap_mov) = engine.tap_max_movement {
                    let mov_frac = if tap_mov > 1.0 {
                        tap_mov / 2905.0
                    } else {
                        tap_mov
                    };
                    gesture.tap_max_movement =
                        validate_tap_max_movement(mov_frac, "engine.tap_max_movement")?;
                }
            }
            if let Some(tap_mov) = raw.tap_max_movement {
                gesture.tap_max_movement = validate_tap_max_movement(tap_mov, "tap_max_movement")?;
            } else if raw.gesture.is_none()
                && raw
                    .engine
                    .as_ref()
                    .and_then(|e| e.tap_max_movement)
                    .is_none()
                && raw.swipe_min_distance.is_some()
            {
                gesture.tap_max_movement = gesture.swipe_min_distance;
            }
        }

        if gesture.tap_min_duration_ms >= gesture.tap_max_duration_ms {
            return Err("tap_min_duration_ms must be < tap_max_duration_ms".to_string());
        }
        config.update_gesture(gesture);

        if let Some(raw_encoder) = raw.encoder {
            config.encoder.enabled = raw_encoder.enabled.unwrap_or(true);
            if let Some(step) = raw_encoder.step_size {
                config.encoder.step_size = step;
            }
            if let Some(dead_zone) = raw_encoder.dead_zone {
                config.encoder.dead_zone = dead_zone;
            }
            if let Some(repeat_ms) = raw_encoder.repeat_interval_ms {
                config.encoder.repeat_interval = Duration::from_millis(repeat_ms);
            }
            config.encoder.sanitize();
        }

        for (index, raw_binding) in raw.gestures.into_iter().enumerate() {
            let binding = GestureBindingConfig::from_raw(index, raw_binding)?;
            let gesture_key = (binding.zone, binding.direction);
            if !gesture_keys.insert(gesture_key) {
                return Err(format!(
                    "duplicate gesture binding {}.{}",
                    zone_name(binding.zone),
                    direction_name(binding.direction)
                ));
            }
            config.gestures.push(binding);
        }

        for (index, raw_slider) in raw.sliders.into_iter().enumerate() {
            let slider = SliderBindingConfig::from_raw(index, raw_slider)?;
            if !slider_zones.insert(slider.zone) {
                return Err(format!(
                    "duplicate slider binding {}",
                    zone_name(slider.zone)
                ));
            }
            config.sliders.push(slider);
        }

        config.validate_slider_gesture_conflicts()?;

        Ok(config)
    }

    pub fn active_edge_widths(&self) -> EdgeWidths {
        let configured = self.configured_edge_widths();
        EdgeWidths {
            left: self.active_zone_edge_width(Zone::Left, configured.left),
            right: self.active_zone_edge_width(Zone::Right, configured.right),
            top: self.active_zone_edge_width(Zone::Top, configured.top),
            bottom: self.active_zone_edge_width(Zone::Bottom, configured.bottom),
        }
    }

    pub fn configured_edge_widths(&self) -> EdgeWidths {
        let mut widths = self.hitbox.resolved_edge_widths();
        if self.edge_width != DEFAULT_EDGE_WIDTH && self.hitbox.edge_width == DEFAULT_EDGE_WIDTH {
            widths = EdgeWidths::all(self.edge_width);
        }
        if let Some(left) = self
            .hitbox
            .left_edge_width
            .or(self.edge_width_overrides.left)
        {
            widths.left = left;
        }
        if let Some(right) = self
            .hitbox
            .right_edge_width
            .or(self.edge_width_overrides.right)
        {
            widths.right = right;
        }
        if let Some(top) = self
            .hitbox
            .top_edge_height
            .or(self.edge_width_overrides.top)
        {
            widths.top = top;
        }
        if let Some(bottom) = self
            .hitbox
            .bottom_edge_height
            .or(self.edge_width_overrides.bottom)
        {
            widths.bottom = bottom;
        }
        widths
    }

    pub fn override_edge_width(&mut self, width: f32) {
        self.hitbox.edge_width = width;
        self.hitbox.left_edge_width = None;
        self.hitbox.right_edge_width = None;
        self.hitbox.top_edge_height = None;
        self.hitbox.bottom_edge_height = None;
        self.sync_from_subsystems();
    }

    pub fn to_toml(&self) -> Result<String, String> {
        let raw = self.to_raw();
        toml::to_string_pretty(&raw).map_err(|err| format!("failed to format TOML: {err}"))
    }

    pub fn to_raw(&self) -> RawEdgepadConfig {
        RawEdgepadConfig {
            device: match &self.device {
                DeviceConfig::Auto => Some("auto".to_string()),
                DeviceConfig::Path(p) => Some(p.display().to_string()),
            },
            hitbox: Some(RawHitboxConfig {
                edge_width: Some(self.hitbox.edge_width),
                left_edge_width: self.hitbox.left_edge_width,
                right_edge_width: self.hitbox.right_edge_width,
                top_edge_height: self.hitbox.top_edge_height,
                bottom_edge_height: self.hitbox.bottom_edge_height,
                corner_width: Some(self.hitbox.corner_width),
                corner_height: Some(self.hitbox.corner_height),
                corner_hitbox: None,
            }),
            gesture: Some(RawGestureConfig {
                swipe_min_distance: Some(self.gesture.swipe_min_distance),
                swipe_max_drift: Some(self.gesture.swipe_max_drift),
                tap_max_movement: Some(self.gesture.tap_max_movement),
                tap_min_duration_ms: Some(self.gesture.tap_min_duration_ms),
                tap_max_duration_ms: Some(self.gesture.tap_max_duration_ms),
                double_tap_timeout_ms: Some(self.gesture.double_tap_timeout_ms),
                double_tap_max_distance: Some(self.gesture.double_tap_max_distance),
                cooldown_ms: Some(self.gesture.cooldown_ms),
            }),
            edge_width: Some(self.hitbox.edge_width),
            left_edge_width: self.hitbox.left_edge_width,
            right_edge_width: self.hitbox.right_edge_width,
            top_edge_width: self.hitbox.top_edge_height,
            bottom_edge_width: self.hitbox.bottom_edge_height,
            tap_min_duration_ms: Some(self.gesture.tap_min_duration_ms),
            tap_max_duration_ms: Some(self.gesture.tap_max_duration_ms),
            double_tap_timeout_ms: Some(self.gesture.double_tap_timeout_ms),
            double_tap_max_distance: Some(self.gesture.double_tap_max_distance),
            swipe_min_distance: Some(self.gesture.swipe_min_distance),
            swipe_max_drift: Some(self.gesture.swipe_max_drift),
            corner_hitbox: Some(self.hitbox.corner_width),
            tap_max_movement: Some(self.gesture.tap_max_movement),
            encoder: Some(RawEncoderConfig {
                enabled: Some(self.encoder.enabled),
                step_size: Some(self.encoder.step_size),
                dead_zone: Some(self.encoder.dead_zone),
                repeat_interval_ms: Some(self.encoder.repeat_interval.as_millis() as u64),
            }),
            gestures: self.gestures.iter().map(|g| g.to_raw()).collect(),
            sliders: self.sliders.iter().map(|s| s.to_raw()).collect(),
            engine: None,
        }
    }

    pub fn default_preset() -> Self {
        let mut config = Self::default();
        config.hitbox.edge_width = 0.12;
        config.gesture.swipe_min_distance = 0.08;
        config.sync_from_subsystems();
        config.gestures = vec![
            GestureBindingConfig {
                zone: Zone::Left,
                direction: GestureDirection::Up,
                action: GestureActionConfig::Key {
                    key_code: 225,
                    key_name: "KEY_BRIGHTNESSUP".to_string(),
                    repeat: 1,
                },
                name: Some("Brightness Up".to_string()),
                enabled: true,
            },
            GestureBindingConfig {
                zone: Zone::Left,
                direction: GestureDirection::Down,
                action: GestureActionConfig::Key {
                    key_code: 224,
                    key_name: "KEY_BRIGHTNESSDOWN".to_string(),
                    repeat: 1,
                },
                name: Some("Brightness Down".to_string()),
                enabled: true,
            },
            GestureBindingConfig {
                zone: Zone::Right,
                direction: GestureDirection::Up,
                action: GestureActionConfig::Key {
                    key_code: 115,
                    key_name: "KEY_VOLUMEUP".to_string(),
                    repeat: 1,
                },
                name: Some("Volume Up".to_string()),
                enabled: true,
            },
            GestureBindingConfig {
                zone: Zone::Right,
                direction: GestureDirection::Down,
                action: GestureActionConfig::Key {
                    key_code: 114,
                    key_name: "KEY_VOLUMEDOWN".to_string(),
                    repeat: 1,
                },
                name: Some("Volume Down".to_string()),
                enabled: true,
            },
        ];
        config.sliders = Vec::new();
        config
    }

    fn active_zone_edge_width(&self, zone: Zone, configured_width: f32) -> f32 {
        let is_active = match zone {
            Zone::Left => {
                self.gestures.iter().any(|b| {
                    matches!(b.zone, Zone::Left | Zone::TopLeft | Zone::BottomLeft) && b.enabled
                }) || self
                    .sliders
                    .iter()
                    .any(|s| s.zone == Zone::Left && s.enabled)
            }
            Zone::Right => {
                self.gestures.iter().any(|b| {
                    matches!(b.zone, Zone::Right | Zone::TopRight | Zone::BottomRight) && b.enabled
                }) || self
                    .sliders
                    .iter()
                    .any(|s| s.zone == Zone::Right && s.enabled)
            }
            Zone::Top => {
                self.gestures.iter().any(|b| {
                    matches!(b.zone, Zone::Top | Zone::TopLeft | Zone::TopRight) && b.enabled
                }) || self
                    .sliders
                    .iter()
                    .any(|s| s.zone == Zone::Top && s.enabled)
            }
            Zone::Bottom => {
                self.gestures.iter().any(|b| {
                    matches!(b.zone, Zone::Bottom | Zone::BottomLeft | Zone::BottomRight)
                        && b.enabled
                }) || self
                    .sliders
                    .iter()
                    .any(|s| s.zone == Zone::Bottom && s.enabled)
            }
            _ => {
                self.gestures.iter().any(|b| b.zone == zone && b.enabled)
                    || self.sliders.iter().any(|s| s.zone == zone && s.enabled)
            }
        };
        if is_active {
            configured_width
        } else {
            0.0
        }
    }

    pub fn slider_specs(&self) -> Vec<SliderSpec> {
        self.sliders
            .iter()
            .filter(|slider| slider.enabled)
            .map(|slider| SliderSpec {
                zone: slider.zone,
                axis: slider.axis,
                step: slider.step,
            })
            .collect()
    }

    pub fn engine_options(&self) -> EngineOptions {
        let mut active = Vec::new();
        for g in &self.gestures {
            if g.enabled {
                active.push(g.zone);
            }
        }
        for s in &self.sliders {
            if s.enabled {
                active.push(s.zone);
            }
        }
        let active_zones = ZoneSet::from_zones(active);

        EngineOptions {
            tap_min_duration: Duration::from_millis(self.tap_min_duration_ms),
            tap_max_duration: Duration::from_millis(self.tap_max_duration_ms),
            tap_max_movement: self.tap_max_movement,
            swipe_min_distance: self.swipe_min_distance,
            swipe_max_drift: self.swipe_max_drift,
            double_tap_timeout: Duration::from_millis(self.double_tap_timeout_ms),
            double_tap_max_distance: self.double_tap_max_distance,
            corner_hitbox: self.corner_hitbox,
            corner_width: self.corner_width,
            corner_height: self.corner_height,
            double_tap_zones: ZoneSet::from_zones(self.gestures.iter().filter_map(|binding| {
                (binding.enabled && binding.direction == GestureDirection::DoubleTap)
                    .then_some(binding.zone)
            })),
            single_tap_zones: ZoneSet::from_zones(self.gestures.iter().filter_map(|binding| {
                (binding.enabled
                    && binding.direction == GestureDirection::Tap
                    && !matches!(
                        binding.zone,
                        Zone::TopLeft | Zone::TopRight | Zone::BottomLeft | Zone::BottomRight
                    ))
                .then_some(binding.zone)
            })),
            active_zones,
            encoder: self.encoder,
        }
    }

    fn validate_slider_gesture_conflicts(&self) -> Result<(), String> {
        for (index, gesture) in self.gestures.iter().enumerate() {
            if !gesture.enabled
                || matches!(
                    gesture.direction,
                    GestureDirection::Tap | GestureDirection::DoubleTap
                )
            {
                continue;
            }
            if self
                .sliders
                .iter()
                .any(|slider| slider.enabled && slider.zone == gesture.zone)
            {
                return Err(format!(
                    "{}.direction={} conflicts with slider {}; slider zones only allow tap or double-tap gestures",
                    gesture_label(index),
                    direction_name(gesture.direction),
                    zone_name(gesture.zone)
                ));
            }
        }
        Ok(())
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DeviceConfig {
    Auto,
    Path(PathBuf),
}

impl DeviceConfig {
    pub fn parse(raw: &str) -> Result<Self, String> {
        raw.parse()
    }

    pub fn resolve(&self, input_root: &Path) -> Result<PathBuf, String> {
        match self {
            Self::Auto => resolve_auto_touchpad(input_root),
            Self::Path(path) => Ok(path.clone()),
        }
    }
}

impl FromStr for DeviceConfig {
    type Err = String;

    fn from_str(raw: &str) -> Result<Self, Self::Err> {
        let value = raw.trim();
        if value.is_empty() {
            return Err("device must be `auto` or an event node path".to_string());
        }
        if value == "auto" {
            Ok(Self::Auto)
        } else {
            Ok(Self::Path(PathBuf::from(value)))
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GestureBindingConfig {
    pub zone: Zone,
    pub direction: GestureDirection,
    pub action: GestureActionConfig,
    pub name: Option<String>,
    pub enabled: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub struct SliderBindingConfig {
    pub zone: Zone,
    pub axis: SliderAxis,
    pub step: f32,
    pub negative: SliderActionConfig,
    pub positive: SliderActionConfig,
    pub name: Option<String>,
    pub enabled: bool,
}

impl SliderBindingConfig {
    pub fn new(
        zone: Zone,
        axis: SliderAxis,
        step: f32,
        negative: SliderActionConfig,
        positive: SliderActionConfig,
    ) -> Self {
        Self {
            zone,
            axis,
            step,
            negative,
            positive,
            name: None,
            enabled: true,
        }
    }

    pub fn action_for(&self, direction: SliderDirection) -> &SliderActionConfig {
        match direction {
            SliderDirection::Up | SliderDirection::Left => &self.negative,
            SliderDirection::Down | SliderDirection::Right => &self.positive,
        }
    }

    pub fn direction_is_valid(&self, direction: SliderDirection) -> bool {
        match self.axis {
            SliderAxis::Vertical => {
                matches!(direction, SliderDirection::Up | SliderDirection::Down)
            }
            SliderAxis::Horizontal => {
                matches!(direction, SliderDirection::Left | SliderDirection::Right)
            }
        }
    }

    pub fn to_raw(&self) -> RawSliderBindingConfig {
        let (up, down, left, right) = match self.axis {
            SliderAxis::Vertical => (
                Some(self.negative.to_raw()),
                Some(self.positive.to_raw()),
                None,
                None,
            ),
            SliderAxis::Horizontal => (
                None,
                None,
                Some(self.negative.to_raw()),
                Some(self.positive.to_raw()),
            ),
        };

        RawSliderBindingConfig {
            zone: zone_name(self.zone).to_string(),
            step: Some(self.step),
            up,
            down,
            left,
            right,
            up_key: None,
            down_key: None,
            left_key: None,
            right_key: None,
            name: self.name.clone(),
            enabled: if !self.enabled { Some(false) } else { None },
        }
    }

    fn from_raw(index: usize, raw: RawSliderBindingConfig) -> Result<Self, String> {
        let label = slider_label(index);
        let zone = parse_zone(&raw.zone)
            .ok_or_else(|| format!("{}.zone must be one of: left, right, top, bottom", label))?;
        if matches!(
            zone,
            Zone::TopLeft | Zone::TopRight | Zone::BottomLeft | Zone::BottomRight
        ) {
            return Err(format!(
                "{label}: sliders are only supported on edge zones (left, right, top, bottom)"
            ));
        }
        let axis = default_slider_axis(zone);
        let step = match raw.step {
            Some(step) => validate_slider_step(step, &format!("{label}.step"))?,
            None => DEFAULT_SLIDER_STEP,
        };
        let (negative, positive) = match axis {
            SliderAxis::Vertical => {
                reject_slider_action(&label, "left", raw.left, raw.left_key)?;
                reject_slider_action(&label, "right", raw.right, raw.right_key)?;
                (
                    parse_required_slider_action(&label, "up", raw.up, raw.up_key)?,
                    parse_required_slider_action(&label, "down", raw.down, raw.down_key)?,
                )
            }
            SliderAxis::Horizontal => {
                reject_slider_action(&label, "up", raw.up, raw.up_key)?;
                reject_slider_action(&label, "down", raw.down, raw.down_key)?;
                (
                    parse_required_slider_action(&label, "left", raw.left, raw.left_key)?,
                    parse_required_slider_action(&label, "right", raw.right, raw.right_key)?,
                )
            }
        };
        let name = raw.name;
        let enabled = raw.enabled.unwrap_or(true);

        Ok(Self {
            zone,
            axis,
            step,
            negative,
            positive,
            name,
            enabled,
        })
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SliderActionConfig {
    Command(CommandActionConfig),
    Key {
        key_code: u16,
        key_name: String,
        repeat: u32,
    },
}

impl SliderActionConfig {
    pub fn argv(&self) -> Option<&[String]> {
        match self {
            Self::Command(cmd) => Some(&cmd.argv),
            Self::Key { .. } => None,
        }
    }

    pub fn to_raw(&self) -> RawSliderActionConfig {
        match self {
            Self::Command(cmd) => RawSliderActionConfig::Command(cmd.argv.clone()),
            Self::Key {
                key_name, repeat, ..
            } => RawSliderActionConfig::Key {
                r#type: None,
                key: key_name.clone(),
                repeat: if *repeat > 1 { Some(*repeat) } else { None },
            },
        }
    }
}

impl From<CommandActionConfig> for SliderActionConfig {
    fn from(cmd: CommandActionConfig) -> Self {
        Self::Command(cmd)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommandActionConfig {
    pub argv: Vec<String>,
}

impl CommandActionConfig {
    pub fn new<I, S>(argv: I) -> Result<Self, String>
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        let argv = argv.into_iter().map(Into::into).collect::<Vec<_>>();
        if argv.is_empty() {
            return Err("command action requires at least a program".to_string());
        }
        Ok(Self { argv })
    }
}

impl GestureBindingConfig {
    pub fn new(zone: Zone, direction: GestureDirection, action: GestureActionConfig) -> Self {
        Self {
            zone,
            direction,
            action,
            name: None,
            enabled: true,
        }
    }

    pub fn matches(&self, gesture: &Gesture) -> bool {
        self.enabled && self.zone == gesture.zone && self.direction == gesture.direction
    }

    pub fn to_raw(&self) -> RawGestureBindingConfig {
        let (action, key, keys) = match &self.action {
            GestureActionConfig::Log => {
                (Some(RawGestureActionConfig::Log { log: true }), None, None)
            }
            GestureActionConfig::Command { argv } => (
                Some(RawGestureActionConfig::Command(argv.clone())),
                None,
                None,
            ),
            GestureActionConfig::Key {
                key_name, repeat, ..
            } if *repeat <= 1 => (None, Some(key_name.clone()), None),
            GestureActionConfig::Key {
                key_name, repeat, ..
            } => (
                Some(RawGestureActionConfig::Key {
                    r#type: None,
                    key: key_name.clone(),
                    repeat: Some(*repeat),
                }),
                None,
                None,
            ),
            GestureActionConfig::KeyCombo { key_names, .. } => {
                (None, None, Some(key_names.clone()))
            }
        };
        RawGestureBindingConfig {
            zone: zone_name(self.zone).to_string(),
            direction: direction_name(self.direction).to_string(),
            action,
            key,
            keys,
            command: None,
            name: self.name.clone(),
            enabled: if !self.enabled { Some(false) } else { None },
        }
    }

    fn from_raw(index: usize, raw: RawGestureBindingConfig) -> Result<Self, String> {
        let label = gesture_label(index);
        let zone = parse_zone(&raw.zone).ok_or_else(|| {
            format!(
                "{}.zone must be one of: left, right, top, bottom, top-left, top-right, bottom-left, bottom-right",
                label
            )
        })?;
        let direction = parse_direction(&raw.direction).ok_or_else(|| {
            format!(
                "{}.direction must be one of: up, down, left, right, tap, double-tap",
                label
            )
        })?;
        if matches!(
            zone,
            Zone::TopLeft | Zone::TopRight | Zone::BottomLeft | Zone::BottomRight
        ) && direction != GestureDirection::DoubleTap
        {
            return Err(format!("{label}: corner zones support double-tap only"));
        }
        let action =
            GestureActionConfig::from_raw(index, raw.action, raw.key, raw.keys, raw.command)?;
        let name = raw.name;
        let enabled = raw.enabled.unwrap_or(true);

        Ok(Self {
            zone,
            direction,
            action,
            name,
            enabled,
        })
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GestureActionConfig {
    Log,
    Command {
        argv: Vec<String>,
    },
    Key {
        key_code: u16,
        key_name: String,
        repeat: u32,
    },
    KeyCombo {
        key_codes: Vec<u16>,
        key_names: Vec<String>,
    },
}

impl GestureActionConfig {
    fn from_raw(
        index: usize,
        raw_action: Option<RawGestureActionConfig>,
        raw_key: Option<String>,
        raw_keys: Option<Vec<String>>,
        raw_command: Option<Vec<String>>,
    ) -> Result<Self, String> {
        if let Some(keys) = raw_keys {
            if keys.is_empty() {
                return Err(format!("{}.keys cannot be empty", gesture_label(index)));
            }
            let mut key_codes = Vec::with_capacity(keys.len());
            let mut key_names = Vec::with_capacity(keys.len());
            for k in &keys {
                let key_code = parse_key_code(k)
                    .map_err(|err| format!("{}.keys: {err}", gesture_label(index)))?;
                let canonical_name = key_code_to_name(key_code);
                key_codes.push(key_code);
                key_names.push(canonical_name);
            }
            return Ok(Self::KeyCombo {
                key_codes,
                key_names,
            });
        }

        if let Some(key_name) = raw_key {
            let key_code = parse_key_code(&key_name)
                .map_err(|err| format!("{}.key: {err}", gesture_label(index)))?;
            let canonical_name = key_code_to_name(key_code);
            return Ok(Self::Key {
                key_code,
                key_name: canonical_name,
                repeat: 1,
            });
        }

        if let Some(argv) = raw_command {
            return Self::command(argv)
                .map_err(|err| format!("{}.command: {err}", gesture_label(index)));
        }

        let raw = raw_action.ok_or_else(|| {
            format!(
                "{}: either 'action', 'key', or 'keys' is required",
                gesture_label(index)
            )
        })?;

        match raw {
            RawGestureActionConfig::LogString(s) => {
                if s.eq_ignore_ascii_case("log") {
                    Ok(Self::Log)
                } else {
                    Err(format!(
                        "{}.action string must be 'log', got '{s}'",
                        gesture_label(index)
                    ))
                }
            }
            RawGestureActionConfig::Command(argv) => {
                Self::command(argv).map_err(|err| format!("{}.action: {err}", gesture_label(index)))
            }
            RawGestureActionConfig::Log { log: true } => Ok(Self::Log),
            RawGestureActionConfig::Log { log: false } => {
                Err(format!("{}.action.log must be true", gesture_label(index)))
            }
            RawGestureActionConfig::Media {
                media_action,
                key,
                repeat,
                ..
            } => {
                let resolved_key = key
                    .or_else(|| {
                        media_action.as_deref().and_then(|act| match act {
                            "play_pause" => Some("KEY_PLAYPAUSE".to_string()),
                            "next" => Some("KEY_NEXTSONG".to_string()),
                            "previous" => Some("KEY_PREVIOUSSONG".to_string()),
                            "stop" => Some("KEY_STOPCD".to_string()),
                            "mute" => Some("KEY_MUTE".to_string()),
                            _ => None,
                        })
                    })
                    .ok_or_else(|| {
                        format!(
                            "{}.action (media) requires a valid key or media_action",
                            gesture_label(index)
                        )
                    })?;
                let key_code = parse_key_code(&resolved_key)
                    .map_err(|err| format!("{}.action.key: {err}", gesture_label(index)))?;
                let canonical_name = key_code_to_name(key_code);
                Ok(Self::Key {
                    key_code,
                    key_name: canonical_name,
                    repeat: repeat.unwrap_or(1).max(1),
                })
            }
            RawGestureActionConfig::Shortcut { keys, .. } => {
                if keys.is_empty() {
                    return Err(format!(
                        "{}.action.keys cannot be empty",
                        gesture_label(index)
                    ));
                }
                let mut key_codes = Vec::with_capacity(keys.len());
                let mut key_names = Vec::with_capacity(keys.len());
                for k in &keys {
                    let key_code = parse_key_code(k)
                        .map_err(|err| format!("{}.action.keys: {err}", gesture_label(index)))?;
                    let canonical_name = key_code_to_name(key_code);
                    key_codes.push(key_code);
                    key_names.push(canonical_name);
                }
                Ok(Self::KeyCombo {
                    key_codes,
                    key_names,
                })
            }
            RawGestureActionConfig::Key { key, repeat, .. } => {
                let key_code = parse_key_code(&key)
                    .map_err(|err| format!("{}.action.key: {err}", gesture_label(index)))?;
                let canonical_name = key_code_to_name(key_code);
                Ok(Self::Key {
                    key_code,
                    key_name: canonical_name,
                    repeat: repeat.unwrap_or(1).max(1),
                })
            }
        }
    }

    pub fn command<I, S>(argv: I) -> Result<Self, String>
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        let argv = argv.into_iter().map(Into::into).collect::<Vec<_>>();
        if argv.is_empty() {
            return Err("command action requires at least a program".to_string());
        }
        Ok(Self::Command { argv })
    }

    pub fn key(name_or_code: &str) -> Result<Self, String> {
        let key_code = parse_key_code(name_or_code)?;
        let key_name = key_code_to_name(key_code);
        Ok(Self::Key {
            key_code,
            key_name,
            repeat: 1,
        })
    }

    pub fn key_with_repeat(name_or_code: &str, repeat: u32) -> Result<Self, String> {
        let key_code = parse_key_code(name_or_code)?;
        let key_name = key_code_to_name(key_code);
        Ok(Self::Key {
            key_code,
            key_name,
            repeat: repeat.max(1),
        })
    }
}

pub const DEFAULT_CONFIG_TEMPLATE: &str = include_str!("../examples/edgepad.toml.example");

/// Result of ensuring a configuration file exists and is valid.
#[derive(Debug, PartialEq)]
pub enum EnsureConfigResult {
    /// An existing valid configuration file was loaded.
    LoadedExisting(EdgepadConfig),
    /// No configuration file existed; initialized a new valid default configuration from template.
    InitializedDefault {
        path: PathBuf,
        config: EdgepadConfig,
    },
    /// The configuration file exists but is malformed. A backup was created without overwriting user data.
    MalformedBackupCreated {
        path: PathBuf,
        backup_path: PathBuf,
        error: String,
    },
}

pub fn load_edgepad_config(path: &Path) -> Result<EdgepadConfig, String> {
    let input = fs::read_to_string(path)
        .map_err(|err| format!("failed to read config {}: {err}", path.display()))?;
    EdgepadConfig::parse(&input)
        .map_err(|err| format!("failed to parse config {}: {err}", path.display()))
}

pub fn resolve_edgepad_config_dir() -> Result<PathBuf, String> {
    if let Some(config_home) = env::var_os("XDG_CONFIG_HOME").filter(|v| !v.is_empty()) {
        Ok(PathBuf::from(config_home).join("edgepad"))
    } else if let Some(home) = env::var_os("HOME").filter(|v| !v.is_empty()) {
        Ok(PathBuf::from(home).join(".config/edgepad"))
    } else {
        Err("failed to resolve user config directory: neither XDG_CONFIG_HOME nor HOME is set".to_string())
    }
}

pub fn resolve_edgepad_data_dir() -> Result<PathBuf, String> {
    if let Some(data_home) = env::var_os("XDG_DATA_HOME").filter(|v| !v.is_empty()) {
        Ok(PathBuf::from(data_home).join("edgepad"))
    } else if let Some(home) = env::var_os("HOME").filter(|v| !v.is_empty()) {
        Ok(PathBuf::from(home).join(".local/share/edgepad"))
    } else {
        Err("failed to resolve user data directory: neither XDG_DATA_HOME nor HOME is set".to_string())
    }
}

pub fn default_edgepad_config_path() -> Result<PathBuf, String> {
    resolve_edgepad_config_dir().map(|dir| dir.join("edgepad.toml"))
}

pub fn ensure_edgepad_config(path: &Path) -> Result<EnsureConfigResult, String> {
    if path.exists() {
        if !path.is_file() {
            return Err(format!("config path is not a file: {}", path.display()));
        }
        let content = fs::read_to_string(path)
            .map_err(|err| format!("failed to read config {}: {err}", path.display()))?;
        match EdgepadConfig::parse(&content) {
            Ok(config) => Ok(EnsureConfigResult::LoadedExisting(config)),
            Err(parse_err) => {
                let timestamp = std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .map(|d| d.as_secs())
                    .unwrap_or(0);
                let backup_dir = path.parent().unwrap_or_else(|| Path::new(".")).join("backups");
                let _ = fs::create_dir_all(&backup_dir);
                let backup_file_name = format!(
                    "{}.bak.{}",
                    path.file_name().and_then(|n| n.to_str()).unwrap_or("edgepad.toml"),
                    timestamp
                );
                let backup_path = backup_dir.join(backup_file_name);
                let _ = fs::copy(path, &backup_path);
                Ok(EnsureConfigResult::MalformedBackupCreated {
                    path: path.to_path_buf(),
                    backup_path,
                    error: parse_err,
                })
            }
        }
    } else {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)
                .map_err(|err| format!("failed to create config directory {}: {err}", parent.display()))?;
            let backups_dir = parent.join("backups");
            let _ = fs::create_dir_all(&backups_dir);
        }

        let template_candidates = [
            PathBuf::from("/usr/share/edgepad/edgepad.toml"),
            PathBuf::from("/usr/local/share/edgepad/edgepad.toml"),
        ];
        let template_content = template_candidates
            .iter()
            .find(|p| p.is_file())
            .and_then(|p| fs::read_to_string(p).ok())
            .unwrap_or_else(|| DEFAULT_CONFIG_TEMPLATE.to_string());

        let config = EdgepadConfig::parse(&template_content)
            .map_err(|err| format!("default config template failed validation: {err}"))?;

        let parent = path.parent().unwrap_or_else(|| Path::new("."));
        let tmp_path = parent.join(format!(".edgepad_cfg_{}.tmp", std::process::id()));
        fs::write(&tmp_path, &template_content)
            .map_err(|err| format!("failed to write temporary config {}: {err}", tmp_path.display()))?;
        fs::rename(&tmp_path, path)
            .map_err(|err| format!("failed to finalize config file {}: {err}", path.display()))?;

        Ok(EnsureConfigResult::InitializedDefault {
            path: path.to_path_buf(),
            config,
        })
    }
}

pub fn parse_edge_width(raw_value: &str) -> Result<f32, String> {
    let parsed = raw_value
        .parse::<f32>()
        .map_err(|_| "--edge-width must be > 0 and < 0.5".to_string())?;
    validate_edge_width(parsed, "--edge-width")
}

fn validate_edge_width(parsed: f32, name: &str) -> Result<f32, String> {
    if !(parsed > 0.0 && parsed < 0.5) {
        return Err(format!("{name} must be > 0 and < 0.5"));
    }
    Ok(parsed)
}

fn validate_optional_edge_width(value: Option<f32>, name: &str) -> Result<Option<f32>, String> {
    value
        .map(|width| validate_edge_width(width, name))
        .transpose()
}

fn validate_slider_step(parsed: f32, name: &str) -> Result<f32, String> {
    if !(parsed > 0.0 && parsed <= 1.0) {
        return Err(format!("{name} must be > 0 and <= 1"));
    }
    Ok(parsed)
}

fn validate_tap_min_duration_ms(parsed: u64, name: &str) -> Result<u64, String> {
    if parsed > 10_000 {
        return Err(format!("{name} must be <= 10000"));
    }
    Ok(parsed)
}

fn validate_tap_max_duration_ms(parsed: u64, name: &str) -> Result<u64, String> {
    if parsed == 0 || parsed > 10000 {
        return Err(format!("{name} must be > 0 and <= 10000"));
    }
    Ok(parsed)
}

fn validate_double_tap_timeout_ms(parsed: u64, name: &str) -> Result<u64, String> {
    if parsed == 0 || parsed > 10000 {
        return Err(format!("{name} must be > 0 and <= 10000"));
    }
    Ok(parsed)
}

fn validate_double_tap_max_distance(parsed: f32, name: &str) -> Result<f32, String> {
    if !parsed.is_finite() || parsed <= 0.0 || parsed > 1.0 {
        return Err(format!("{name} must be > 0 and <= 1"));
    }
    Ok(parsed)
}

fn validate_swipe_min_distance(parsed: f32, name: &str) -> Result<f32, String> {
    if !(parsed > 0.0 && parsed <= 1.0) {
        return Err(format!("{name} must be > 0 and <= 1"));
    }
    Ok(parsed)
}

fn validate_swipe_max_drift(parsed: f32, name: &str) -> Result<f32, String> {
    if !(parsed > 0.0 && parsed <= 1.0) {
        return Err(format!("{name} must be > 0 and <= 1"));
    }
    Ok(parsed)
}

fn validate_tap_max_movement(parsed: f32, name: &str) -> Result<f32, String> {
    if !parsed.is_finite() || parsed <= 0.0 || parsed > 1.0 {
        return Err(format!("{name} must be > 0 and <= 1"));
    }
    Ok(parsed)
}

fn validate_corner_hitbox(parsed: f32, name: &str) -> Result<f32, String> {
    if !parsed.is_finite() || parsed < MIN_CORNER_HITBOX || parsed > MAX_CORNER_HITBOX {
        return Err(format!(
            "{name} must be between {MIN_CORNER_HITBOX} and {MAX_CORNER_HITBOX}"
        ));
    }
    Ok(parsed)
}

fn resolve_auto_touchpad(input_root: &Path) -> Result<PathBuf, String> {
    let report = discover_device_report(input_root)
        .map_err(|err| format!("failed to list {}: {err}", input_root.display()))?;
    resolve_auto_touchpad_from_report(input_root, &report)
}

fn resolve_auto_touchpad_from_report(
    input_root: &Path,
    report: &DiscoveryReport,
) -> Result<PathBuf, String> {
    if report.event_node_count == 0 {
        return Err(format!(
            "device=auto found no event devices under {}",
            input_root.display()
        ));
    }

    if report.summaries.is_empty() {
        return Err(format!(
            "device=auto found no readable event devices under {} ({}; try sudo, group input, or seat/logind ACLs)",
            input_root.display(),
            event_node_count_text(report.event_node_count)
        ));
    }

    let candidates = touchpad_candidates(&report.summaries);
    match candidates.as_slice() {
        [] => Err(format!(
            "device=auto found no touchpad candidates under {} (readable non-touchpad devices: {})",
            input_root.display(),
            report.summaries.len()
        )),
        [candidate] => Ok(candidate.path.clone()),
        _ => {
            let mut message = format!(
                "device=auto matched multiple touchpad candidates under {}; pass --device <event-node> explicitly",
                input_root.display()
            );
            for candidate in candidates {
                message.push_str("\n  ");
                message.push_str(&format_device_line(candidate));
            }
            Err(message)
        }
    }
}

fn parse_zone(raw: &str) -> Option<Zone> {
    match raw {
        "left" => Some(Zone::Left),
        "right" => Some(Zone::Right),
        "top" => Some(Zone::Top),
        "bottom" => Some(Zone::Bottom),
        "top-left" | "top_left" => Some(Zone::TopLeft),
        "top-right" | "top_right" => Some(Zone::TopRight),
        "bottom-left" | "bottom_left" => Some(Zone::BottomLeft),
        "bottom-right" | "bottom_right" => Some(Zone::BottomRight),
        _ => None,
    }
}

fn parse_direction(raw: &str) -> Option<GestureDirection> {
    match raw {
        "up" => Some(GestureDirection::Up),
        "down" => Some(GestureDirection::Down),
        "left" => Some(GestureDirection::Left),
        "right" => Some(GestureDirection::Right),
        "tap" => Some(GestureDirection::Tap),
        "double-tap" => Some(GestureDirection::DoubleTap),
        _ => None,
    }
}

fn zone_name(zone: Zone) -> &'static str {
    match zone {
        Zone::Left => "left",
        Zone::Right => "right",
        Zone::Top => "top",
        Zone::Bottom => "bottom",
        Zone::TopLeft => "top-left",
        Zone::TopRight => "top-right",
        Zone::BottomLeft => "bottom-left",
        Zone::BottomRight => "bottom-right",
    }
}

fn direction_name(direction: GestureDirection) -> &'static str {
    match direction {
        GestureDirection::Up => "up",
        GestureDirection::Down => "down",
        GestureDirection::Left => "left",
        GestureDirection::Right => "right",
        GestureDirection::Tap => "tap",
        GestureDirection::DoubleTap => "double-tap",
    }
}

fn default_slider_axis(zone: Zone) -> SliderAxis {
    match zone {
        Zone::Left | Zone::Right | Zone::TopLeft | Zone::BottomLeft => SliderAxis::Vertical,
        Zone::Top | Zone::Bottom | Zone::TopRight | Zone::BottomRight => SliderAxis::Horizontal,
    }
}

fn parse_required_slider_action(
    label: &str,
    direction: &str,
    raw: Option<RawSliderActionConfig>,
    raw_key: Option<String>,
) -> Result<SliderActionConfig, String> {
    if let Some(key_name) = raw_key {
        let key_code =
            parse_key_code(&key_name).map_err(|err| format!("{label}.{direction}_key: {err}"))?;
        let canonical_name = key_code_to_name(key_code);
        return Ok(SliderActionConfig::Key {
            key_code,
            key_name: canonical_name,
            repeat: 1,
        });
    }

    let action = raw.ok_or_else(|| format!("{label}.{direction} is required"))?;
    match action {
        RawSliderActionConfig::LogString(s) => Err(format!(
            "{label}.{direction}: expected command array or key table, got '{s}'"
        )),
        RawSliderActionConfig::Command(argv) => {
            if argv.is_empty() {
                return Err(format!(
                    "{label}.{direction}: command action requires at least a program"
                ));
            }
            Ok(SliderActionConfig::Command(CommandActionConfig { argv }))
        }
        RawSliderActionConfig::Key { key, repeat, .. } => {
            let key_code =
                parse_key_code(&key).map_err(|err| format!("{label}.{direction}.key: {err}"))?;
            let canonical_name = key_code_to_name(key_code);
            Ok(SliderActionConfig::Key {
                key_code,
                key_name: canonical_name,
                repeat: repeat.unwrap_or(1).max(1),
            })
        }
    }
}

fn reject_slider_action(
    label: &str,
    direction: &str,
    raw: Option<RawSliderActionConfig>,
    raw_key: Option<String>,
) -> Result<(), String> {
    if raw.is_some() || raw_key.is_some() {
        return Err(format!(
            "{label}.{direction} is not valid for this slider zone"
        ));
    }
    Ok(())
}

fn event_node_count_text(count: usize) -> String {
    if count == 1 {
        "1 event node was present but could not be opened".to_string()
    } else {
        format!("{count} event nodes were present but could not be opened")
    }
}

fn gesture_label(index: usize) -> String {
    format!("gestures[{index}]")
}

fn slider_label(index: usize) -> String {
    format!("sliders[{index}]")
}

#[derive(Debug, Deserialize, Serialize, Clone, Default)]
pub struct RawHitboxConfig {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub edge_width: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub left_edge_width: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub right_edge_width: Option<f32>,
    #[serde(alias = "top_edge_width", skip_serializing_if = "Option::is_none")]
    pub top_edge_height: Option<f32>,
    #[serde(alias = "bottom_edge_width", skip_serializing_if = "Option::is_none")]
    pub bottom_edge_height: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub corner_width: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub corner_height: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub corner_hitbox: Option<f32>,
}

#[derive(Debug, Deserialize, Serialize, Clone, Default)]
pub struct RawGestureConfig {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub swipe_min_distance: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub swipe_max_drift: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tap_max_movement: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tap_min_duration_ms: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tap_max_duration_ms: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub double_tap_timeout_ms: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub double_tap_max_distance: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cooldown_ms: Option<u64>,
}

#[derive(Debug, Deserialize, Serialize, Clone, Default)]
pub struct RawEdgepadConfig {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub device: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub hitbox: Option<RawHitboxConfig>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub gesture: Option<RawGestureConfig>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub edge_width: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub left_edge_width: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub right_edge_width: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub top_edge_width: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bottom_edge_width: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tap_min_duration_ms: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tap_max_duration_ms: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub double_tap_timeout_ms: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub double_tap_max_distance: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub swipe_min_distance: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub swipe_max_drift: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub corner_hitbox: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tap_max_movement: Option<f32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub encoder: Option<RawEncoderConfig>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub engine: Option<RawEngineConfig>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub gestures: Vec<RawGestureBindingConfig>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub sliders: Vec<RawSliderBindingConfig>,
}

#[derive(Debug, Deserialize, Serialize, Clone, Default, PartialEq)]
pub struct RawEngineConfig {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub min_travel: Option<f32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max_drift: Option<f32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cooldown_ms: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tap_max_duration_ms: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tap_max_movement: Option<f32>,
}

#[derive(Debug, Deserialize, Serialize, Clone, Default, PartialEq)]
pub struct RawEncoderConfig {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub enabled: Option<bool>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub step_size: Option<f32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub dead_zone: Option<f32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub repeat_interval_ms: Option<u64>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct RawGestureBindingConfig {
    #[serde(alias = "edge")]
    pub zone: String,
    pub direction: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub action: Option<RawGestureActionConfig>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub key: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub keys: Option<Vec<String>>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub command: Option<Vec<String>>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub enabled: Option<bool>,
}

#[derive(Debug, Deserialize, Serialize, Clone, PartialEq)]
#[serde(untagged)]
pub enum RawGestureActionConfig {
    LogString(String),
    Command(Vec<String>),
    Log {
        log: bool,
    },
    Shortcut {
        #[serde(default)]
        r#type: Option<String>,
        keys: Vec<String>,
    },
    Media {
        #[serde(default)]
        r#type: Option<String>,
        #[serde(default)]
        media_action: Option<String>,
        key: Option<String>,
        #[serde(default)]
        repeat: Option<u32>,
    },
    Key {
        #[serde(default)]
        r#type: Option<String>,
        key: String,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        repeat: Option<u32>,
    },
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct RawSliderBindingConfig {
    #[serde(alias = "edge")]
    pub zone: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub step: Option<f32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub up: Option<RawSliderActionConfig>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub down: Option<RawSliderActionConfig>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub left: Option<RawSliderActionConfig>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub right: Option<RawSliderActionConfig>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub up_key: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub down_key: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub left_key: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub right_key: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub enabled: Option<bool>,
}

#[derive(Debug, Deserialize, Serialize, Clone, PartialEq)]
#[serde(untagged)]
pub enum RawSliderActionConfig {
    LogString(String),
    Command(Vec<String>),
    Key {
        #[serde(default)]
        r#type: Option<String>,
        key: String,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        repeat: Option<u32>,
    },
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::device::{AxisInfo, DeviceKind, DeviceSummary};

    #[test]
    fn device_config_parses_auto_and_path() {
        assert_eq!(DeviceConfig::parse("auto"), Ok(DeviceConfig::Auto));
        assert_eq!(
            DeviceConfig::parse("/dev/input/event7"),
            Ok(DeviceConfig::Path(PathBuf::from("/dev/input/event7")))
        );
    }

    #[test]
    fn auto_device_resolution_reports_empty_root() {
        let report = DiscoveryReport {
            summaries: Vec::new(),
            event_node_count: 0,
            unreadable_count: 0,
        };

        let result = resolve_auto_touchpad_from_report(Path::new("/tmp/input"), &report);

        assert_eq!(
            result.as_ref().err().map(String::as_str),
            Some("device=auto found no event devices under /tmp/input")
        );
    }

    #[test]
    fn auto_device_resolution_selects_single_touchpad_candidate() {
        let report = DiscoveryReport {
            summaries: vec![device_summary(
                "/dev/input/event5",
                "Example Touchpad",
                DeviceKind::Touchpad,
            )],
            event_node_count: 1,
            unreadable_count: 0,
        };

        let result = resolve_auto_touchpad_from_report(Path::new("/dev/input"), &report);

        assert_eq!(result, Ok(PathBuf::from("/dev/input/event5")));
    }

    #[test]
    fn auto_device_resolution_rejects_ambiguous_touchpads() {
        let report = DiscoveryReport {
            summaries: vec![
                device_summary("/dev/input/event5", "First Touchpad", DeviceKind::Touchpad),
                device_summary("/dev/input/event6", "Second Touchpad", DeviceKind::Touchpad),
            ],
            event_node_count: 2,
            unreadable_count: 0,
        };

        let result = resolve_auto_touchpad_from_report(Path::new("/dev/input"), &report)
            .expect_err("ambiguous auto resolution should fail");

        assert!(result.contains("device=auto matched multiple touchpad candidates"));
        assert!(result.contains("/dev/input/event5"));
        assert!(result.contains("/dev/input/event6"));
    }

    #[test]
    fn edgepad_config_parses_device_edge_width_and_gesture_bindings() {
        let config = EdgepadConfig::parse(
            r#"
            device = "/dev/input/event7"
            edge_width = 0.20
            tap_min_duration_ms = 90
            swipe_min_distance = 0.03

            [[gestures]]
            zone = "left"
            direction = "right"
            action = { log = true }

            [[gestures]]
            zone = "right"
            direction = "down"
            action = ["notify-send", "edgepad", "right-down"]
            "#,
        )
        .expect("config should parse");

        assert_eq!(
            config.device,
            DeviceConfig::Path(PathBuf::from("/dev/input/event7"))
        );
        assert_eq!(config.edge_width, 0.20);
        assert_eq!(config.edge_width_overrides, EdgeWidthOverrides::default());
        assert_eq!(config.tap_min_duration_ms, 90);
        assert_eq!(config.swipe_min_distance, 0.03);
        assert_eq!(
            config.engine_options().tap_min_duration,
            Duration::from_millis(90)
        );
        assert_eq!(config.engine_options().swipe_min_distance, 0.03);
        assert_eq!(
            config.gestures,
            vec![
                GestureBindingConfig {
                    zone: Zone::Left,
                    direction: GestureDirection::Right,
                    action: GestureActionConfig::Log,
                    name: None,
                    enabled: true,
                },
                GestureBindingConfig {
                    zone: Zone::Right,
                    direction: GestureDirection::Down,
                    action: GestureActionConfig::Command {
                        argv: vec![
                            "notify-send".to_string(),
                            "edgepad".to_string(),
                            "right-down".to_string(),
                        ],
                    },
                    name: None,
                    enabled: true,
                },
            ]
        );
    }

    #[test]
    fn edgepad_config_defaults_tap_sequence_thresholds() {
        let config = EdgepadConfig::parse(
            r#"
            [[gestures]]
            zone = "left"
            direction = "tap"
            action = ["pamixer", "-t"]
            "#,
        )
        .expect("config should parse");

        assert_eq!(config.tap_min_duration_ms, DEFAULT_TAP_MIN_DURATION_MS);
        assert_eq!(config.tap_max_duration_ms, DEFAULT_TAP_MAX_DURATION_MS);
        assert_eq!(config.double_tap_timeout_ms, DEFAULT_DOUBLE_TAP_TIMEOUT_MS);
        assert_eq!(
            config.double_tap_max_distance,
            DEFAULT_DOUBLE_TAP_MAX_DISTANCE
        );
        assert_eq!(config.swipe_min_distance, DEFAULT_SWIPE_MIN_DISTANCE);
    }

    #[test]
    fn edgepad_config_parses_double_tap_binding_and_sequence_thresholds() {
        let config = EdgepadConfig::parse(
            r#"
            tap_min_duration_ms = 30
            tap_max_duration_ms = 220
            double_tap_timeout_ms = 360
            double_tap_max_distance = 0.05

            [[gestures]]
            zone = "top"
            direction = "tap"
            action = ["playerctl", "play-pause"]

            [[gestures]]
            zone = "top"
            direction = "double-tap"
            action = ["playerctl", "stop"]
            "#,
        )
        .expect("double-tap config should parse");

        let options = config.engine_options();
        assert_eq!(options.tap_min_duration, Duration::from_millis(30));
        assert_eq!(options.tap_max_duration, Duration::from_millis(220));
        assert_eq!(options.double_tap_timeout, Duration::from_millis(360));
        assert_eq!(options.double_tap_max_distance, 0.05);
        assert!(options.double_tap_zones.contains(Zone::Top));
        assert!(options.single_tap_zones.contains(Zone::Top));
        assert_eq!(config.gestures[1].direction, GestureDirection::DoubleTap);
    }

    #[test]
    fn invalid_gesture_direction_lists_double_tap_as_an_allowed_value() {
        let result = EdgepadConfig::parse(
            r#"
            [[gestures]]
            zone = "top"
            direction = "doubletap"
            action = { log = true }
            "#,
        );

        assert_eq!(
            result.as_ref().err().map(String::as_str),
            Some("gestures[0].direction must be one of: up, down, left, right, tap, double-tap")
        );
    }

    #[test]
    fn edgepad_config_activates_only_zones_with_gesture_bindings() {
        let config = EdgepadConfig::parse(
            r#"
            edge_width = 0.20

            [[gestures]]
            zone = "right"
            direction = "up"
            action = ["notify-send", "right-up"]

            [[gestures]]
            zone = "top"
            direction = "left"
            action = ["notify-send", "top-left"]
            "#,
        )
        .expect("config should parse");

        assert_eq!(
            config.active_edge_widths(),
            EdgeWidths {
                left: 0.0,
                right: 0.20,
                top: 0.20,
                bottom: 0.0,
            }
        );
    }

    #[test]
    fn edgepad_config_applies_optional_per_edge_widths_with_global_fallback() {
        let config = EdgepadConfig::parse(
            r#"
            edge_width = 0.10
            left_edge_width = 0.08
            top_edge_width = 0.16

            [[gestures]]
            zone = "left"
            direction = "down"
            action = { log = true }

            [[gestures]]
            zone = "right"
            direction = "down"
            action = { log = true }

            [[gestures]]
            zone = "top"
            direction = "right"
            action = { log = true }
            "#,
        )
        .expect("config should parse");

        assert_eq!(
            config.edge_width_overrides,
            EdgeWidthOverrides {
                left: Some(0.08),
                right: None,
                top: Some(0.16),
                bottom: None,
            }
        );
        assert_eq!(
            config.configured_edge_widths(),
            EdgeWidths {
                left: 0.08,
                right: 0.10,
                top: 0.16,
                bottom: 0.10,
            }
        );
        assert_eq!(
            config.active_edge_widths(),
            EdgeWidths {
                left: 0.08,
                right: 0.10,
                top: 0.16,
                bottom: 0.0,
            }
        );
    }

    #[test]
    fn edgepad_config_rejects_invalid_per_edge_width() {
        let err = EdgepadConfig::parse(
            r#"
            edge_width = 0.10
            right_edge_width = 0.50
            "#,
        )
        .expect_err("invalid per-edge width should fail");

        assert_eq!(err, "right_edge_width must be > 0 and < 0.5");
    }

    #[test]
    fn global_edge_width_override_clears_per_edge_widths() {
        let mut config = EdgepadConfig::parse(
            r#"
            edge_width = 0.10
            left_edge_width = 0.08
            right_edge_width = 0.16
            "#,
        )
        .expect("config should parse");

        config.override_edge_width(0.20);

        assert_eq!(config.edge_width, 0.20);
        assert_eq!(config.edge_width_overrides, EdgeWidthOverrides::default());
        assert_eq!(config.configured_edge_widths(), EdgeWidths::all(0.20));
    }

    #[test]
    fn edgepad_config_parses_vertical_slider_with_default_step() {
        let config = EdgepadConfig::parse(
            r#"
            edge_width = 0.20

            [[sliders]]
            zone = "left"
            up = ["pamixer", "-d", "3"]
            down = ["pamixer", "-i", "3"]
            "#,
        )
        .expect("config should parse");

        assert_eq!(config.sliders.len(), 1);
        assert_eq!(config.sliders[0].zone, Zone::Left);
        assert_eq!(config.sliders[0].axis, SliderAxis::Vertical);
        assert_eq!(config.sliders[0].step, DEFAULT_SLIDER_STEP);
        assert_eq!(
            config.sliders[0].negative.argv(),
            Some(&["pamixer".to_string(), "-d".to_string(), "3".to_string()][..])
        );
        assert_eq!(
            config.sliders[0].positive.argv(),
            Some(&["pamixer".to_string(), "-i".to_string(), "3".to_string()][..])
        );
        assert_eq!(
            config.active_edge_widths(),
            EdgeWidths {
                left: 0.20,
                right: 0.0,
                top: 0.0,
                bottom: 0.0,
            }
        );
        assert_eq!(
            config.slider_specs(),
            vec![SliderSpec {
                zone: Zone::Left,
                axis: SliderAxis::Vertical,
                step: DEFAULT_SLIDER_STEP,
            }]
        );
    }

    #[test]
    fn edgepad_config_parses_horizontal_slider_with_custom_step() {
        let config = EdgepadConfig::parse(
            r#"
            [[sliders]]
            zone = "top"
            step = 0.08
            left = ["playerctl", "previous"]
            right = ["playerctl", "next"]
            "#,
        )
        .expect("config should parse");

        assert_eq!(config.sliders.len(), 1);
        assert_eq!(config.sliders[0].zone, Zone::Top);
        assert_eq!(config.sliders[0].axis, SliderAxis::Horizontal);
        assert_eq!(config.sliders[0].step, 0.08);
    }

    #[test]
    fn edgepad_config_rejects_excessive_tap_min_duration() {
        let result = EdgepadConfig::parse(
            r#"
            tap_min_duration_ms = 10001

            [[gestures]]
            zone = "left"
            direction = "tap"
            action = ["pamixer", "-t"]
            "#,
        );

        assert_eq!(
            result.as_ref().err().map(String::as_str),
            Some("tap_min_duration_ms must be <= 10000")
        );
    }

    #[test]
    fn edgepad_config_rejects_empty_tap_duration_range() {
        let result = EdgepadConfig::parse(
            r#"
            tap_min_duration_ms = 180
            tap_max_duration_ms = 180
            "#,
        );

        assert_eq!(
            result.as_ref().err().map(String::as_str),
            Some("tap_min_duration_ms must be < tap_max_duration_ms")
        );
    }

    #[test]
    fn edgepad_config_rejects_invalid_double_tap_thresholds() {
        let timeout = EdgepadConfig::parse("double_tap_timeout_ms = 0");
        assert_eq!(
            timeout.as_ref().err().map(String::as_str),
            Some("double_tap_timeout_ms must be > 0 and <= 10000")
        );

        let distance = EdgepadConfig::parse("double_tap_max_distance = 0.0");
        assert_eq!(
            distance.as_ref().err().map(String::as_str),
            Some("double_tap_max_distance must be > 0 and <= 1")
        );
    }

    #[test]
    fn edgepad_config_rejects_invalid_swipe_min_distance() {
        let result = EdgepadConfig::parse(
            r#"
            swipe_min_distance = 0.0

            [[gestures]]
            zone = "left"
            direction = "tap"
            action = ["pamixer", "-t"]
            "#,
        );

        assert_eq!(
            result.as_ref().err().map(String::as_str),
            Some("swipe_min_distance must be > 0 and <= 1")
        );
    }

    #[test]
    fn edgepad_config_rejects_duplicate_gesture_binding() {
        let result = EdgepadConfig::parse(
            r#"
            [[gestures]]
            zone = "left"
            direction = "right"
            action = { log = true }

            [[gestures]]
            zone = "left"
            direction = "right"
            action = ["notify-send", "duplicate"]
            "#,
        );

        assert_eq!(
            result.as_ref().err().map(String::as_str),
            Some("duplicate gesture binding left.right")
        );
    }

    #[test]
    fn edgepad_config_rejects_duplicate_slider_zone() {
        let result = EdgepadConfig::parse(
            r#"
            [[sliders]]
            zone = "right"
            up = ["brightnessctl", "set", "5%-"]
            down = ["brightnessctl", "set", "+5%"]

            [[sliders]]
            zone = "right"
            up = ["brightnessctl", "set", "5%-"]
            down = ["brightnessctl", "set", "+5%"]
            "#,
        );

        assert_eq!(
            result.as_ref().err().map(String::as_str),
            Some("duplicate slider binding right")
        );
    }

    #[test]
    fn edgepad_config_rejects_directional_gesture_on_slider_zone() {
        let result = EdgepadConfig::parse(
            r#"
            [[gestures]]
            zone = "left"
            direction = "up"
            action = ["notify-send", "left-up"]

            [[sliders]]
            zone = "left"
            up = ["pamixer", "-d", "3"]
            down = ["pamixer", "-i", "3"]
            "#,
        );

        assert_eq!(
            result.as_ref().err().map(String::as_str),
            Some("gestures[0].direction=up conflicts with slider left; slider zones only allow tap or double-tap gestures")
        );
    }

    #[test]
    fn edgepad_config_allows_tap_gesture_on_slider_zone() {
        let config = EdgepadConfig::parse(
            r#"
            [[gestures]]
            zone = "left"
            direction = "tap"
            action = ["pamixer", "-t"]

            [[sliders]]
            zone = "left"
            up = ["pamixer", "-d", "3"]
            down = ["pamixer", "-i", "3"]
            "#,
        )
        .expect("tap and slider can share a zone");

        assert_eq!(config.gestures.len(), 1);
        assert_eq!(config.sliders.len(), 1);
    }

    #[test]
    fn edgepad_config_allows_double_tap_gesture_on_slider_zone() {
        let config = EdgepadConfig::parse(
            r#"
            [[gestures]]
            zone = "left"
            direction = "double-tap"
            action = ["pamixer", "-t"]

            [[sliders]]
            zone = "left"
            up = ["pamixer", "-d", "3"]
            down = ["pamixer", "-i", "3"]
            "#,
        )
        .expect("double-tap and slider can share a zone");

        assert_eq!(config.gestures.len(), 1);
        assert_eq!(config.sliders.len(), 1);
    }

    #[test]
    fn edgepad_config_rejects_empty_command_action_array() {
        let result = EdgepadConfig::parse(
            r#"
            [[gestures]]
            zone = "top"
            direction = "right"
            action = []
            "#,
        );

        assert_eq!(
            result.as_ref().err().map(String::as_str),
            Some("gestures[0].action: command action requires at least a program")
        );
    }

    #[test]
    fn gesture_binding_matches_recognized_gesture() {
        let binding = GestureBindingConfig {
            zone: Zone::Top,
            direction: GestureDirection::Down,
            action: GestureActionConfig::Log,
            name: None,
            enabled: true,
        };
        let gesture = Gesture {
            zone: Zone::Top,
            direction: GestureDirection::Down,
            slot: 0,
            tracking_id: 10,
        };

        assert!(binding.matches(&gesture));
    }

    fn device_summary(path: &str, name: &str, kind: DeviceKind) -> DeviceSummary {
        DeviceSummary {
            path: PathBuf::from(path),
            name: name.to_string(),
            vendor: 0x1234,
            product: 0x5678,
            kind,
            slot_range: matches!(kind, DeviceKind::Touchpad | DeviceKind::Touchscreen)
                .then_some(AxisInfo { min: 0, max: 4 }),
            x_range: matches!(kind, DeviceKind::Touchpad | DeviceKind::Touchscreen)
                .then_some(AxisInfo { min: 0, max: 1000 }),
            y_range: matches!(kind, DeviceKind::Touchpad | DeviceKind::Touchscreen)
                .then_some(AxisInfo { min: 0, max: 700 }),
        }
    }
}
