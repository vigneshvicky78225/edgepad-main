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
pub use crate::core::{
    DEFAULT_DOUBLE_TAP_MAX_DISTANCE, DEFAULT_DOUBLE_TAP_TIMEOUT_MS, DEFAULT_SWIPE_MIN_DISTANCE,
    DEFAULT_TAP_MAX_DURATION_MS, DEFAULT_TAP_MIN_DURATION_MS,
};

#[derive(Debug, Clone, PartialEq)]
pub struct EdgepadConfig {
    pub device: DeviceConfig,
    pub edge_width: f32,
    pub edge_width_overrides: EdgeWidthOverrides,
    pub tap_min_duration_ms: u64,
    pub tap_max_duration_ms: u64,
    pub double_tap_timeout_ms: u64,
    pub double_tap_max_distance: f32,
    pub swipe_min_distance: f32,
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
        Self {
            device: DeviceConfig::Auto,
            edge_width: DEFAULT_EDGE_WIDTH,
            edge_width_overrides: EdgeWidthOverrides::default(),
            tap_min_duration_ms: DEFAULT_TAP_MIN_DURATION_MS,
            tap_max_duration_ms: DEFAULT_TAP_MAX_DURATION_MS,
            double_tap_timeout_ms: DEFAULT_DOUBLE_TAP_TIMEOUT_MS,
            double_tap_max_distance: DEFAULT_DOUBLE_TAP_MAX_DISTANCE,
            swipe_min_distance: DEFAULT_SWIPE_MIN_DISTANCE,
            encoder: crate::encoder::EncoderConfig::default(),
            gestures: Vec::new(),
            sliders: Vec::new(),
        }
    }
}

impl EdgepadConfig {
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
        if let Some(edge_width) = raw.edge_width {
            config.edge_width = validate_edge_width(edge_width, "edge_width")?;
        }
        config.edge_width_overrides = EdgeWidthOverrides {
            left: validate_optional_edge_width(raw.left_edge_width, "left_edge_width")?,
            right: validate_optional_edge_width(raw.right_edge_width, "right_edge_width")?,
            top: validate_optional_edge_width(raw.top_edge_width, "top_edge_width")?,
            bottom: validate_optional_edge_width(raw.bottom_edge_width, "bottom_edge_width")?,
        };
        if let Some(tap_min_duration_ms) = raw.tap_min_duration_ms {
            config.tap_min_duration_ms =
                validate_tap_min_duration_ms(tap_min_duration_ms, "tap_min_duration_ms")?;
        }
        if let Some(tap_max_duration_ms) = raw.tap_max_duration_ms {
            config.tap_max_duration_ms =
                validate_tap_max_duration_ms(tap_max_duration_ms, "tap_max_duration_ms")?;
        }
        if config.tap_min_duration_ms >= config.tap_max_duration_ms {
            return Err("tap_min_duration_ms must be < tap_max_duration_ms".to_string());
        }
        if let Some(double_tap_timeout_ms) = raw.double_tap_timeout_ms {
            config.double_tap_timeout_ms =
                validate_double_tap_timeout_ms(double_tap_timeout_ms, "double_tap_timeout_ms")?;
        }
        if let Some(double_tap_max_distance) = raw.double_tap_max_distance {
            config.double_tap_max_distance = validate_double_tap_max_distance(
                double_tap_max_distance,
                "double_tap_max_distance",
            )?;
        }
        if let Some(swipe_min_distance) = raw.swipe_min_distance {
            config.swipe_min_distance =
                validate_swipe_min_distance(swipe_min_distance, "swipe_min_distance")?;
        }
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
        EdgeWidths {
            left: self.edge_width_overrides.left.unwrap_or(self.edge_width),
            right: self.edge_width_overrides.right.unwrap_or(self.edge_width),
            top: self.edge_width_overrides.top.unwrap_or(self.edge_width),
            bottom: self.edge_width_overrides.bottom.unwrap_or(self.edge_width),
        }
    }

    pub fn override_edge_width(&mut self, width: f32) {
        self.edge_width = width;
        self.edge_width_overrides = EdgeWidthOverrides::default();
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
            edge_width: Some(self.edge_width),
            left_edge_width: self.edge_width_overrides.left,
            right_edge_width: self.edge_width_overrides.right,
            top_edge_width: self.edge_width_overrides.top,
            bottom_edge_width: self.edge_width_overrides.bottom,
            tap_min_duration_ms: Some(self.tap_min_duration_ms),
            tap_max_duration_ms: Some(self.tap_max_duration_ms),
            double_tap_timeout_ms: Some(self.double_tap_timeout_ms),
            double_tap_max_distance: Some(self.double_tap_max_distance),
            swipe_min_distance: Some(self.swipe_min_distance),
            encoder: Some(RawEncoderConfig {
                enabled: Some(self.encoder.enabled),
                step_size: Some(self.encoder.step_size),
                dead_zone: Some(self.encoder.dead_zone),
                repeat_interval_ms: Some(self.encoder.repeat_interval.as_millis() as u64),
            }),
            gestures: self.gestures.iter().map(|g| g.to_raw()).collect(),
            sliders: self.sliders.iter().map(|s| s.to_raw()).collect(),
        }
    }

    pub fn default_preset() -> Self {
        Self {
            device: DeviceConfig::Auto,
            edge_width: 0.12,
            edge_width_overrides: EdgeWidthOverrides::default(),
            tap_min_duration_ms: DEFAULT_TAP_MIN_DURATION_MS,
            tap_max_duration_ms: DEFAULT_TAP_MAX_DURATION_MS,
            double_tap_timeout_ms: DEFAULT_DOUBLE_TAP_TIMEOUT_MS,
            double_tap_max_distance: DEFAULT_DOUBLE_TAP_MAX_DISTANCE,
            swipe_min_distance: 0.08,
            encoder: crate::encoder::EncoderConfig::default(),
            gestures: vec![
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
            ],
            sliders: Vec::new(),
        }
    }

    fn active_zone_edge_width(&self, zone: Zone, configured_width: f32) -> f32 {
        if self.gestures.iter().any(|binding| binding.zone == zone && binding.enabled)
            || self.sliders.iter().any(|binding| binding.zone == zone && binding.enabled)
        {
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
        EngineOptions {
            tap_min_duration: Duration::from_millis(self.tap_min_duration_ms),
            tap_max_duration: Duration::from_millis(self.tap_max_duration_ms),
            swipe_min_distance: self.swipe_min_distance,
            double_tap_timeout: Duration::from_millis(self.double_tap_timeout_ms),
            double_tap_max_distance: self.double_tap_max_distance,
            double_tap_zones: ZoneSet::from_zones(self.gestures.iter().filter_map(|binding| {
                (binding.enabled && binding.direction == GestureDirection::DoubleTap)
                    .then_some(binding.zone)
            })),
            single_tap_zones: ZoneSet::from_zones(self.gestures.iter().filter_map(|binding| {
                (binding.enabled && binding.direction == GestureDirection::Tap)
                    .then_some(binding.zone)
            })),
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
        RawGestureBindingConfig {
            zone: zone_name(self.zone).to_string(),
            direction: direction_name(self.direction).to_string(),
            action: Some(match &self.action {
                GestureActionConfig::Log => RawGestureActionConfig::Log { log: true },
                GestureActionConfig::Command { argv } => RawGestureActionConfig::Command(argv.clone()),
                GestureActionConfig::Key { key_name, repeat, .. } => RawGestureActionConfig::Key {
                    key: key_name.clone(),
                    repeat: if *repeat > 1 { Some(*repeat) } else { None },
                },
            }),
            key: None,
            name: self.name.clone(),
            enabled: if !self.enabled { Some(false) } else { None },
        }
    }

    fn from_raw(index: usize, raw: RawGestureBindingConfig) -> Result<Self, String> {
        let label = gesture_label(index);
        let zone = parse_zone(&raw.zone)
            .ok_or_else(|| format!("{}.zone must be one of: left, right, top, bottom", label))?;
        let direction = parse_direction(&raw.direction).ok_or_else(|| {
            format!(
                "{}.direction must be one of: up, down, left, right, tap, double-tap",
                label
            )
        })?;
        let action = GestureActionConfig::from_raw(index, raw.action, raw.key)?;
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
    Command { argv: Vec<String> },
    Key {
        key_code: u16,
        key_name: String,
        repeat: u32,
    },
}

impl GestureActionConfig {
    fn from_raw(
        index: usize,
        raw_action: Option<RawGestureActionConfig>,
        raw_key: Option<String>,
    ) -> Result<Self, String> {
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

        let raw = raw_action.ok_or_else(|| {
            format!(
                "{}: either 'action' or 'key' is required",
                gesture_label(index)
            )
        })?;

        match raw {
            RawGestureActionConfig::Command(argv) => {
                Self::command(argv).map_err(|err| format!("{}.action: {err}", gesture_label(index)))
            }
            RawGestureActionConfig::Log { log: true } => Ok(Self::Log),
            RawGestureActionConfig::Log { log: false } => {
                Err(format!("{}.action.log must be true", gesture_label(index)))
            }
            RawGestureActionConfig::Key { key, repeat } => {
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

pub fn load_edgepad_config(path: &Path) -> Result<EdgepadConfig, String> {
    let input = fs::read_to_string(path)
        .map_err(|err| format!("failed to read config {}: {err}", path.display()))?;
    EdgepadConfig::parse(&input)
        .map_err(|err| format!("failed to parse config {}: {err}", path.display()))
}

pub fn default_edgepad_config_path() -> Result<PathBuf, String> {
    if let Some(config_home) = env::var_os("XDG_CONFIG_HOME").filter(|value| !value.is_empty()) {
        return Ok(PathBuf::from(config_home).join("edgepad/edgepad.toml"));
    }

    if let Some(home) = env::var_os("HOME").filter(|value| !value.is_empty()) {
        return Ok(PathBuf::from(home).join(".config/edgepad/edgepad.toml"));
    }

    Err(
        "config path was not provided; pass --config <file> or set XDG_CONFIG_HOME/HOME"
            .to_string(),
    )
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
        Zone::Left | Zone::Right => SliderAxis::Vertical,
        Zone::Top | Zone::Bottom => SliderAxis::Horizontal,
    }
}

fn parse_required_slider_action(
    label: &str,
    direction: &str,
    raw: Option<RawSliderActionConfig>,
    raw_key: Option<String>,
) -> Result<SliderActionConfig, String> {
    if let Some(key_name) = raw_key {
        let key_code = parse_key_code(&key_name)
            .map_err(|err| format!("{label}.{direction}_key: {err}"))?;
        let canonical_name = key_code_to_name(key_code);
        return Ok(SliderActionConfig::Key {
            key_code,
            key_name: canonical_name,
            repeat: 1,
        });
    }

    let action = raw.ok_or_else(|| format!("{label}.{direction} is required"))?;
    match action {
        RawSliderActionConfig::Command(argv) => {
            if argv.is_empty() {
                return Err(format!(
                    "{label}.{direction}: command action requires at least a program"
                ));
            }
            Ok(SliderActionConfig::Command(CommandActionConfig { argv }))
        }
        RawSliderActionConfig::Key { key, repeat } => {
            let key_code = parse_key_code(&key)
                .map_err(|err| format!("{label}.{direction}.key: {err}"))?;
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

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct RawEdgepadConfig {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub device: Option<String>,
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
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub encoder: Option<RawEncoderConfig>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub gestures: Vec<RawGestureBindingConfig>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub sliders: Vec<RawSliderBindingConfig>,
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
    pub name: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub enabled: Option<bool>,
}

#[derive(Debug, Deserialize, Serialize, Clone, PartialEq)]
#[serde(untagged)]
pub enum RawGestureActionConfig {
    Command(Vec<String>),
    Log { log: bool },
    Key {
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
    Command(Vec<String>),
    Key {
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
