from roboflow import Roboflow

rf = Roboflow(api_key="rf_TcGxfal9JCVRet0sPW5b5JUXIGO2")
project = rf.workspace("roboflow-universe-projects").project("ambulance-detection-tlhe3")
dataset = project.version(2).download("yolov8")
print("Done:", dataset.location)