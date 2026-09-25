"""Local video editing via ffmpeg (stdlib subprocess; no other deps).

Transparency: every command prints the exact ffmpeg invocation before it
runs. Safety: outputs may never overwrite inputs; missing inputs and
missing ffmpeg are refused with clear messages (see video/SETUP.md).

Edit plans (video/plans.py) store clip/trim/concat/filter steps as JSON and
execute them in order with temp intermediates.
"""
