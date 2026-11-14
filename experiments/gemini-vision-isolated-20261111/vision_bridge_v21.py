"""Encrypted, build-bound Design RAG V2.1 screenshot capsule (advisory only)."""
import base64, hashlib, io, json, os, re
from pathlib import Path
from PIL import Image
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

SCHEMA="generic-design-rag-v2.1-vision-capsule"
CONTEXT=b"moksha-vision-bridge-v2.1"
HEX=re.compile(r"^[a-f0-9]{64}$")
NAME=re.compile(r"^[a-z0-9_-]+\.html$")
PROJECT=re.compile(r"^[a-z][a-z0-9_-]{1,62}$")
WIDTHS=(390,1440)

def check(ok,code):
    if not ok:raise ValueError(code)
def digest(b):return hashlib.sha256(b).hexdigest()
def enc(b):return base64.b64encode(b).decode()
def dec(v):return base64.b64decode(v,validate=True)
def canon(o):return json.dumps(o,sort_keys=True,separators=(",",":")).encode()

def gather(w):
    from core import state,sha,treehash
    w=Path(w).resolve(strict=True)
    s=state(w)
    check(s.get("version") in ("2.0.0","2.1.0","2.1.4"),"ENGINE_VERSION_DENIED")
    check(bool(PROJECT.fullmatch(s.get("project",""))),"PROJECT_INVALID")
    check(s["site_sha256"]==treehash(w/"site"),"SOURCE_DRIFT")
    qa=w/"reports/browser-qa.json"
    check(qa.is_file() and not qa.is_symlink() and sha(qa)==s.get("qa_receipt_sha256"),"QA_DRIFT")
    data=json.loads(qa.read_text())
    check(data.get("pass") is True and data.get("source_hash")==s["site_sha256"],"QA_SOURCE_MISMATCH")
    items=data.get("screenshots",[])
    pages={x.get("page") for x in items if isinstance(x,dict)}
    check(len(pages)==6 and all(isinstance(p,str) and NAME.fullmatch(p) for p in pages),"SIX_PAGES_REQUIRED")
    selected=[x for x in items if x["width"] in WIDTHS]
    check(len(selected)==12 and {(x["page"],x["width"]) for x in selected}=={(p,z) for p in pages for z in WIDTHS},"EXACT_12_PAIRS_REQUIRED")
    images=[]
    for x in sorted(selected,key=lambda a:(a["page"],a["width"])):
        name=x.get("name","")
        check(Path(name).name==name and name not in ("",".",".."),"UNSAFE_NAME")
        file=w/"evidence/screenshots"/name
        check(file.is_file() and not file.is_symlink() and file.stat().st_size<=3000000,"IMAGE_UNSAFE")
        raw=file.read_bytes()
        check(digest(raw)==x.get("sha256"),"IMAGE_HASH_MISMATCH")
        with Image.open(io.BytesIO(raw)) as original:
            im=original.convert("RGB");im.thumbnail((384,512))
            bf=io.BytesIO();im.save(bf,"JPEG",quality=52,optimize=True)
        jpeg=bf.getvalue()
        check(100<len(jpeg)<=200000,"JPEG_SIZE_INVALID")
        images.append({"page":x["page"],"width":x["width"],"name":name,
            "raw_sha256":x["sha256"],"jpeg_sha256":digest(jpeg),"jpeg_b64":enc(jpeg)})
    metadata={"schema":SCHEMA,"project":s["project"],"job_id":s.get("job_id"),
        "engine_version":s["version"],"site_sha256":s["site_sha256"],
        "qa_receipt_sha256":s["qa_receipt_sha256"],"pages":sorted(pages),
        "count":12,"model":"gemini-3.5-flash-lite","artistic_score":None,
        "independently_attested":False,"production_release_allowed":False}
    return {"manifest":metadata,"images":images}

def seal(w,recipient_public_key_b64,output):
    pub=dec(recipient_public_key_b64)
    check(len(pub)==32,"BAD_RECIPIENT_PUBLIC_KEY")
    payload=canon(gather(w))
    check(len(payload)<=14000000,"PAYLOAD_TOO_LARGE")
    ephemeral=X25519PrivateKey.generate()
    public=ephemeral.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    aes_key=HKDF(algorithm=hashes.SHA256(),length=32,salt=None,info=CONTEXT).derive(
        ephemeral.exchange(X25519PublicKey.from_public_bytes(pub)))
    nonce=os.urandom(12)
    encrypted=AESGCM(aes_key).encrypt(nonce,payload,CONTEXT)
    blob={"schema":SCHEMA,"ephemeral_public":enc(public),"nonce":enc(nonce),
          "ciphertext":enc(encrypted),"sha256":digest(encrypted)}
    output=Path(output).expanduser()
    check(not output.exists() and not output.is_symlink(),"OUTPUT_ALREADY_EXISTS")
    output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    check(not output.parent.is_symlink(),"OUTPUT_DIR_SYMLINK")
    fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as f:
        f.write(canon(blob)+b"\n");f.flush();os.fsync(f.fileno())
    return {"status":"ENCRYPTED_LOCAL_ONLY","sha256":digest(output.read_bytes()),
        "pages":6,"screenshots":12,"transfer":"NOT_CONFIGURED",
        "release_authorized":False,"artistic_score":None}

def open_capsule(blob_bytes,recipient_material_b64,expected_project,expected_site,expected_qa):
    check(len(blob_bytes)<=28000000,"CAPSULE_SIZE_DENIED")
    material=dec(recipient_material_b64)
    check(len(material)==32,"RECIPIENT_KEY_INVALID")
    capsule=json.loads(blob_bytes)
    check(capsule.get("schema")==SCHEMA,"SCHEMA_DENIED")
    ciphertext=dec(capsule["ciphertext"])
    check(digest(ciphertext)==capsule.get("sha256"),"CAPSULE_HASH_MISMATCH")
    key=HKDF(algorithm=hashes.SHA256(),length=32,salt=None,info=CONTEXT).derive(
        X25519PrivateKey.from_private_bytes(material).exchange(
            X25519PublicKey.from_public_bytes(dec(capsule["ephemeral_public"]))))
    plaintext=AESGCM(key).decrypt(dec(capsule["nonce"]),ciphertext,CONTEXT)
    document=json.loads(plaintext)
    m=document["manifest"]
    check(m.get("schema")==SCHEMA and m.get("count")==12,"CAPSULE_MANIFEST_INVALID")
    check(bool(PROJECT.fullmatch(expected_project)) and m["project"]==expected_project,"PROJECT_MISMATCH")
    check(bool(HEX.fullmatch(expected_site)) and m["site_sha256"]==expected_site,"SITE_MISMATCH")
    check(bool(HEX.fullmatch(expected_qa)) and m["qa_receipt_sha256"]==expected_qa,"QA_MISMATCH")
    check(m.get("artistic_score") is None and m.get("production_release_allowed") is False,"RELEASE_FLAG_DENIED")
    images=document["images"]
    check(len(images)==12,"CAPSULE_PARTIAL")
    pairs=set()
    for item in images:
        pair=(item["page"],item["width"])
        check(pair not in pairs and pair[0] in m["pages"] and pair[1] in WIDTHS,"DUPLICATE_OR_UNEXPECTED_PAIR")
        pairs.add(pair)
        jpeg=dec(item["jpeg_b64"])
        check(len(jpeg)<=200000 and digest(jpeg)==item["jpeg_sha256"],"JPEG_HASH_MISMATCH")
    check(pairs=={(p,w) for p in m["pages"] for w in WIDTHS},"COVERAGE_MISMATCH")
    return document
