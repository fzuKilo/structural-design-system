"""
Evaluator configuration for structural design assessment
Defines weights, scoring curves, and construction requirements for different structure types
"""

try:
    from .scoring_curve import MultiLevelScoringCurve
except ImportError:
    from scoring_curve import MultiLevelScoringCurve


# ============================================================================
# Dimension Weights Configuration
# ============================================================================

WEIGHTS_CONFIG = {
    'beam': {
        'safety': 0.40,          # Safety 40% (strength 20% + stiffness 15% + construction 5%)
        'economy': 0.25,         # Economy 25%
        'efficiency': 0.20,      # Structural efficiency 20%
        'sustainability': 0.15   # Sustainability 15%
    },
    'cantilever_beam': {
        'safety': 0.45,          # Cantilever beam: higher safety priority
        'economy': 0.20,
        'efficiency': 0.20,
        'sustainability': 0.15
    },
    'continuous_beam': {
        'safety': 0.40,
        'economy': 0.25,
        'efficiency': 0.20,
        'sustainability': 0.15
    },
    'truss': {
        'safety': 0.35,          # Truss: higher redundancy, economy more important
        'economy': 0.30,
        'efficiency': 0.20,
        'sustainability': 0.15
    },
    'frame': {
        'safety': 0.45,          # Frame: critical structure, highest safety priority
        'economy': 0.20,
        'efficiency': 0.20,
        'sustainability': 0.15
    }
}


# ============================================================================
# Scoring Curves Configuration
# ============================================================================

SCORING_CURVES = {
    'beam': {
        'stress': MultiLevelScoringCurve(
            excellent_range=(0.65, 0.75),  # Beam: conservative
            good_range=(0.60, 0.80),
            acceptable_range=(0.50, 0.90),
            peak_position=0.70
        ),
        'deflection': MultiLevelScoringCurve(
            excellent_range=(0.70, 0.80),
            good_range=(0.65, 0.85),
            acceptable_range=(0.55, 0.95),
            peak_position=0.75
        )
    },

    'cantilever_beam': {
        'stress': MultiLevelScoringCurve(
            excellent_range=(0.60, 0.70),  # Cantilever beam: more conservative
            good_range=(0.55, 0.75),
            acceptable_range=(0.45, 0.85),
            peak_position=0.65
        ),
        'deflection': MultiLevelScoringCurve(
            excellent_range=(0.65, 0.75),  # Stricter deflection control
            good_range=(0.60, 0.80),
            acceptable_range=(0.50, 0.90),
            peak_position=0.70
        )
    },

    'continuous_beam': {
        'stress': MultiLevelScoringCurve(
            excellent_range=(0.63, 0.73),  # Continuous beam: slightly conservative (ref: DES v2.0)
            good_range=(0.58, 0.78),
            acceptable_range=(0.48, 0.88),
            peak_position=0.68
        ),
        'deflection': MultiLevelScoringCurve(
            excellent_range=(0.63, 0.73),
            good_range=(0.58, 0.78),
            acceptable_range=(0.48, 0.88),
            peak_position=0.68
        )
    },

    'truss': {
        'stress': MultiLevelScoringCurve(
            excellent_range=(0.45, 0.55),  # Truss: optimal utilization 0.50 (ref: DES v2.0)
            good_range=(0.40, 0.60),
            acceptable_range=(0.30, 0.70),
            peak_position=0.50
        ),
        'deflection': MultiLevelScoringCurve(
            excellent_range=(0.45, 0.55),
            good_range=(0.40, 0.60),
            acceptable_range=(0.30, 0.70),
            peak_position=0.50
        )
    },

    'frame': {
        'stress': MultiLevelScoringCurve(
            excellent_range=(0.60, 0.70),  # Frame: most conservative
            good_range=(0.55, 0.75),
            acceptable_range=(0.45, 0.85),
            peak_position=0.65
        ),
        'deflection': MultiLevelScoringCurve(
            excellent_range=(0.65, 0.75),
            good_range=(0.60, 0.80),
            acceptable_range=(0.50, 0.90),
            peak_position=0.70
        )
    }
}


# ============================================================================
# Deflection Limits Configuration
# ============================================================================

def get_deflection_limit(structure_type: str, length: float) -> float:
    """
    Get deflection limit for a given structure type

    Args:
        structure_type: Structure type identifier
        length: Span length in meters

    Returns:
        Deflection limit in meters
    """
    DEFLECTION_LIMITS = {
        'beam': lambda L: L / 250,              # Simply supported beam: L/250
        'cantilever_beam': lambda L: L / 200,   # Cantilever beam: L/200 (stricter)
        'continuous_beam': lambda L: L / 300,   # Continuous beam: L/300 (stricter)
        'truss': lambda L: L / 250,             # Truss: L/250
        'frame': lambda L: L / 300,             # Frame: L/300 (stricter)
    }

    limit_func = DEFLECTION_LIMITS.get(structure_type, lambda L: L / 250)
    return limit_func(length)


# ============================================================================
# Construction Requirements Configuration
# ============================================================================

CONSTRUCTION_REQUIREMENTS = {
    'beam': {
        'height_span_ratio': (0.05, 0.15),  # (min, max) - 1/20 to 1/10
        'width_height_ratio': (0.33, 0.67),  # 1/3 to 1/1.5
        'min_width': 0.2,                    # meters
        'min_height': 0.3                    # meters
    },
    'cantilever_beam': {
        'height_span_ratio': (0.08, 0.20),  # Cantilever: larger height/span ratio
        'width_height_ratio': (0.33, 0.67),
        'min_width': 0.2,
        'min_height': 0.3
    },
    'continuous_beam': {
        'height_span_ratio': (0.04, 0.12),  # Continuous: can be more slender
        'width_height_ratio': (0.33, 0.67),
        'min_width': 0.2,
        'min_height': 0.3
    },
    'truss': {
        'height_span_ratio': (0.05, 0.20),
        'slenderness_ratio_compression': 150,  # Maximum for compression members
        'slenderness_ratio_tension': 350,      # Maximum for tension members
        'min_section_area': 500                # mm²
    },
    'frame': {
        'height_span_ratio': (0.08, 0.15),
        'width_height_ratio': (0.33, 0.67),
        'min_column_width': 0.3,
        'min_column_height': 0.3,
        'min_beam_width': 0.2,
        'min_beam_height': 0.3
    }
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_weights(structure_type: str) -> dict:
    """Get dimension weights for a structure type"""
    return WEIGHTS_CONFIG.get(structure_type, WEIGHTS_CONFIG['beam'])


def get_scoring_curves(structure_type: str) -> dict:
    """Get scoring curves for a structure type"""
    return SCORING_CURVES.get(structure_type, SCORING_CURVES['beam'])


def get_construction_requirements(structure_type: str) -> dict:
    """Get construction requirements for a structure type"""
    return CONSTRUCTION_REQUIREMENTS.get(structure_type, CONSTRUCTION_REQUIREMENTS['beam'])


# ============================================================================
# Alert Thresholds Configuration
# ============================================================================

ALERT_THRESHOLDS = {
    "default": {
        "safety_severe": 60,
        "safety_warning": 70,
        "economy_severe": 60,
        "economy_warning": 70,
    },
    "cantilever_beam": {
        "safety_severe": 65,
        "safety_warning": 75,
        "economy_severe": 55,
        "economy_warning": 65,
    },
    "frame": {
        "safety_severe": 65,
        "safety_warning": 75,
        "economy_severe": 55,
        "economy_warning": 65,
    },
    "truss": {
        "safety_severe": 55,
        "safety_warning": 65,
        "economy_severe": 65,
        "economy_warning": 75,
    },
}


def get_alert_thresholds(structure_type: str) -> dict:
    """Get alert thresholds for a structure type"""
    return ALERT_THRESHOLDS.get(structure_type, ALERT_THRESHOLDS["default"])
