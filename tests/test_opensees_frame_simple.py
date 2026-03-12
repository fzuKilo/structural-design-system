"""
Simple standalone test for FrameAnalyzer
"""

import openseespy.opensees as ops

# Test basic OpenSeesPy functionality
print("Testing OpenSeesPy...")

# Simple frame: 1 bay, 1 story
ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

# Create nodes
# Node numbering:
# 3 ----- 4
# |       |
# 0 ----- 1

ops.node(0, 0.0, 0.0)
ops.node(1, 6.0, 0.0)
ops.node(2, 0.0, 4.0)
ops.node(3, 6.0, 4.0)

# Fix column bases
ops.fix(0, 1, 1, 1)
ops.fix(1, 1, 1, 1)

# Material properties
E = 30e9  # Pa
A_col = 0.4 * 0.4  # m^2
I_col = (0.4 * 0.4**3) / 12  # m^4
A_beam = 0.3 * 0.6  # m^2
I_beam = (0.3 * 0.6**3) / 12  # m^4

# Create elements
# Columns
ops.element('elasticBeamColumn', 1, 0, 2, A_col, E, I_col, 1)
ops.element('elasticBeamColumn', 2, 1, 3, A_col, E, I_col, 1)

# Beam
ops.element('elasticBeamColumn', 3, 2, 3, A_beam, E, I_beam, 1)

# Apply loads
ops.timeSeries('Linear', 1)
ops.pattern('Plain', 1, 1)

# Beam distributed load
ops.eleLoad('-ele', 3, '-type', '-beamUniform', -10000, 0.0)

# Lateral load
ops.load(2, 2500, 0.0, 0.0)
ops.load(3, 2500, 0.0, 0.0)

# Analyze
ops.system('BandGeneral')
ops.numberer('RCM')
ops.constraints('Plain')
ops.integrator('LoadControl', 1.0)
ops.algorithm('Linear')
ops.analysis('Static')

ok = ops.analyze(1)

if ok == 0:
    print("✅ Analysis successful!")

    # Get displacements
    disp_2 = ops.nodeDisp(2)
    disp_3 = ops.nodeDisp(3)

    print(f"Node 2 displacement: ux={disp_2[0]*1000:.2f} mm, uy={disp_2[1]*1000:.2f} mm")
    print(f"Node 3 displacement: ux={disp_3[0]*1000:.2f} mm, uy={disp_3[1]*1000:.2f} mm")

    # Calculate story drift
    story_drift = abs(disp_2[0] - 0.0)  # Horizontal displacement
    story_height = 4.0
    drift_ratio = story_drift / story_height

    print(f"Story drift: {story_drift*1000:.2f} mm")
    print(f"Drift ratio: {drift_ratio:.6f} (1/{1/drift_ratio:.0f})")

    # Get forces
    forces_beam = ops.eleForce(3)
    print(f"Beam moment at node 2: {forces_beam[2]/1000:.2f} kN·m")
    print(f"Beam moment at node 3: {forces_beam[5]/1000:.2f} kN·m")

    print("\n🎉 OpenSeesPy frame test passed!")
else:
    print("❌ Analysis failed!")
