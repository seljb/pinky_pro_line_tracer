# `pinky_line_alignment/calibration.py` 사용설명서

**내부 보정·바닥 변환·독립 오차 검증을 수행합니다.**

## 목차

1. [파일 역할](#파일-역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [확인 방법](#확인-방법)
5. [오류와 주의사항](#오류와-주의사항)

## 파일 역할

내부 보정·바닥 변환·독립 오차 검증을 수행합니다. 원본은 [pinky_line_alignment/calibration.py](../../../../../pinky_line_alignment/calibration.py)입니다.

주요 진입점: `intrinsic`, `floor`, `validate`, `main`.

## 사용 순서

intrinsic → floor → validate 순서로 실제 측정 파일을 사용하세요.

명령은 별도 표시가 없으면 저장소 루트 `pinky_pro_line_tracer/`에서 실행합니다. Python 명령은 의존성을 설치한 환경에서 실행합니다. ROS 명령은 Jazzy 환경을 source한 터미널에서 실행합니다.

## 입력과 출력

intrinsic은 체커보드 8장 이상, floor는 대응점 4개 이상, validate는 별도 검증점 5개 이상을 요구합니다.

## 확인 방법

```bash
python -m pinky_line_alignment.calibration --help
python -m pinky_line_alignment.calibration intrinsic --help
python -m pinky_line_alignment.calibration floor --help
python -m pinky_line_alignment.calibration validate --help
```
실측 파일을 입력하는 전체 절차는 루트 README의 카메라 보정 절을 따릅니다. `validate()`는 입력 사전을 직접 갱신하며 실제 점의 독립성을 자동으로 판별하지 않습니다.

오프라인 확인은 `bash scripts/verify_offline.sh`로 실행합니다. 기존 기준은 16개 시험 통과와 좌·우 합성 시나리오 READY 도달입니다. ROS 노드와 실제 장비 연동은 이 검사에 포함되지 않습니다.

## 오류와 주의사항

fit RMSE와 독립 검증 RMSE는 다릅니다. --mark-valid는 물리 측정을 대신하지 않습니다.

[전체 파일 목차](../../../README.md)
