import atlas_pipeline as AP, stage_gate as SG
print(AP.submit('stage6-gatech-build3', ['gatech'], stages=[('build', 'school', 'PY $TOOLS/pi_hierarchy.py {school}', 'project', 2, '16G', '02:00:00')], guard_preempt=True, repo=str(SG.CODE)))
