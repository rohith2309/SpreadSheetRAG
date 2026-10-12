import zipfile
import os

with zipfile.ZipFile('deployment.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('deploy'):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, 'deploy')
            zinfo = zipfile.ZipInfo.from_file(file_path, arcname)
            # Force UNIX permissions: read/execute for all
            zinfo.external_attr = 0o755 << 16 
            with open(file_path, 'rb') as f:
                zf.writestr(zinfo, f.read())