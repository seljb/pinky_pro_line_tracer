# `config/real_calibration_template.json` 사용설명서

**실측 보정 파일의 필드 형식을 보여줍니다.**

## 목차

1. [파일 역할](#파일-역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [확인 방법](#확인-방법)
5. [오류와 주의사항](#오류와-주의사항)

## 파일 역할

실측 보정 파일의 필드 형식을 보여줍니다. 원본은 [config/real_calibration_template.json](../../../../../config/real_calibration_template.json)입니다.

## 사용 순서

형식만 참고하고 calibration CLI로 실측 결과를 생성하세요.

명령은 별도 표시가 없으면 저장소 루트 `pinky_pro_line_tracer/`에서 실행합니다. Python 명령은 의존성을 설치한 환경에서 실행합니다. ROS 명령은 Jazzy 환경을 source한 터미널에서 실행합니다.

## 입력과 출력

호모그래피가 null이므로 Calibration.load에서 거절되는 것이 정상입니다.

## 확인 방법

JSON을 읽을 수 있는지 확인한 뒤 보정 종류·해상도·단위를 검토합니다. JSON 문법 통과는 실물 보정 성공을 뜻하지 않습니다. 자세한 실행은 [루트 안내](../../../../../README.md)를 따르세요.

## 오류와 주의사항

validated 값을 수동으로 true로 바꾸지 마세요.

[전체 파일 목차](../../../README.md)
