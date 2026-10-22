# Speech regions of a recording: pyannote segmentation 3.0 + CAM++ embeddings via sherpa-onnx
# (clustering forced high: we only need where speech is, not who). Writes <workdir>/speech.json = [[s, e], ...].
# usage (via tr.py speech): python speech.py <workdir>
import json, os, sys, tarfile, urllib.request, wave
import numpy as np, sherpa_onnx

W = sys.argv[1]
MD = os.path.expanduser(os.environ.get("ASR_MODELS", "~/asr-models")) + "/speaker"
REL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/"
SEG = f"{MD}/sherpa-onnx-pyannote-segmentation-3-0/model.onnx"
EMB = f"{MD}/3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx"
os.makedirs(MD, exist_ok=True)
if not os.path.exists(SEG):
    tgz = f"{MD}/seg.tar.bz2"
    urllib.request.urlretrieve(REL + "speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2", tgz)
    tarfile.open(tgz).extractall(MD); os.remove(tgz)
if not os.path.exists(EMB):
    urllib.request.urlretrieve(REL + "speaker-recongition-models/" + os.path.basename(EMB), EMB)   # sic: "recongition"

with wave.open(f"{W}/audio/raw16.wav") as f:
    a = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
cfg = sherpa_onnx.OfflineSpeakerDiarizationConfig(
    segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
        pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=SEG), num_threads=8),
    embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=EMB, num_threads=8),
    clustering=sherpa_onnx.FastClusteringConfig(num_clusters=8, threshold=0.5),
    min_duration_on=0.3, min_duration_off=0.5)
res = sherpa_onnx.OfflineSpeakerDiarization(cfg).process(a).sort_by_start_time()
segs = [[round(r.start, 3), round(r.end, 3)] for r in res]
json.dump(segs, open(f"{W}/speech.json", "w"))
print(len(segs), "speech segments,", round(sum(e - s for s, e in segs) / 60, 1), "min")
