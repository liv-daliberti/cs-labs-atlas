# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/reviewed_image_leadership.py (sha256 848004279f678092e0506a2564ed7d5e0aa4cbdca82252c130aa57dd972a33a8); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Root-reviewed official team-image captions, with immutable source/region proof.

The pinned package supplies nine exact Chinese role captions across eight units.
This is reviewed image transcription, not HTML text or face identification.
"""
import hashlib,importlib.util,json
from pathlib import Path
from common import ROOT
FORMAT='reviewed_official_unit_image_role_v1'
PACKAGE='cs17_china_image_leadership_corrected'
MANIFEST_SHA256='f221ba7beb08289f2d3834fd21a1b9b7eb9816c2a7c3a511dfc2d996de543f44'
def validate(review,meta,sources,lab):
 folder=ROOT/'data/reviews'/PACKAGE
 manifest=folder/'freeze_manifest.json'
 assert hashlib.sha256(manifest.read_bytes()).hexdigest()==MANIFEST_SHA256,'Reviewed image package manifest changed'
 for f in json.loads(manifest.read_text())['files']:
  path=(folder/f['path']).resolve();assert path.is_relative_to(folder.resolve())
  raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==f['sha256'] and len(raw)==f['size'],'Reviewed image package changed'
 spec=importlib.util.spec_from_file_location('reviewed_cs17_image_roles',folder/'image_role_validator.py')
 helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 return helper.validate_image_role(review,meta,sources,lab,ROOT,folder)
