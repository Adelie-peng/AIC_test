from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from PIL import Image
import io
import subprocess
import os

# 감정 분석 모듈 import (예외 처리에 집중하므로 실제 로직은 간단화)
from app.emotion.fer_emotion import analyze_facial_expression
from app.emotion.ser_emotion import analyze_voice_emotion_korean
from app.audio.stt import transcribe_audio, load_whisper_model
from app.multimodal.vlm import summarize_scene, load_smol_vlm
from app.nlp.llm import generate_response

router = APIRouter(prefix="/api/emotion", tags=["emotion"])

# 모델 미리 로딩
whisper_model = load_whisper_model()
processor, vlm_model, device = load_smol_vlm()

def convert_webm_to_wav(input_path, output_path):
    command = [
        "ffmpeg", "-y", "-i", input_path, "-ar", "16000", "-ac", "1", output_path
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

@router.post("/analyze")
async def analyze_emotion(
    image: UploadFile = File(...),
    audio: UploadFile = File(...),
    text: str = Form("")
):
    try:
        print("\n📥 분석 요청 수신")
        print("- 이미지 파일명:", image.filename)
        print("- 오디오 파일명:", audio.filename)
        print("- 텍스트 내용:", text)

        # 이미지 처리
        image_bytes = await image.read()
        print("- 이미지 크기:", len(image_bytes))
        if not image_bytes:
            raise ValueError("이미지 파일이 비어 있음")

        pil_image = Image.open(io.BytesIO(image_bytes))

        # 얼굴 감정 분석
        face_emotion = analyze_facial_expression(pil_image)
        print("✅ 얼굴 감정 분석 결과:", face_emotion)

        # 오디오 처리
        audio_path = "temp_debug.webm"
        wav_path = "temp_debug.wav"

        with open(audio_path, "wb") as f:
            f.write(await audio.read())
        print("- 오디오 저장 완료:", audio_path)

        convert_webm_to_wav(audio_path, wav_path)
        print("- 오디오 변환 완료:", wav_path)

        voice_emotion = analyze_voice_emotion_korean(wav_path)
        print("✅ 음성 감정 분석 결과:", voice_emotion)

        transcribed_text = transcribe_audio(whisper_model, wav_path)
        print("✅ STT 결과:", transcribed_text)

        # 장면 분석
        scene = summarize_scene(pil_image, processor, vlm_model, device)
        print("✅ 장면 요약:", scene)

        # LLM 응답 생성
        final_text = transcribed_text or text or ""
        context = {
            "weather": "맑음",
            "sleep": "7시간",
            "stress": "보통",
            "location_scene": scene,
            "emotion_history": [face_emotion, voice_emotion]
        }

        response = generate_response(face_emotion, voice_emotion, scene, final_text, context)
        print("✅ Gemini 응답 완료")

        # 清理临时文件
        if os.path.exists(audio_path):
            os.remove(audio_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)

        return JSONResponse(content={
            "success": True,
            "face": face_emotion,
            "voice": voice_emotion,
            "scene": scene,
            "text": final_text,
            "response": response
        })

    except Exception as e:
        import traceback
        print("❌ 오류 발생:")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

