## Srodowiska
- PC: `~/dev_ws` (symulacja Gazebo, RViz, joy_node i teleop; dongle pada jest na PC). `mjasic@jasicPC`.
- Pi 5: `~/ros2_ws` (prawdziwy robot, dostep przez SSH). `mjasic@RPi5`, logowanie: `ssh mjasic@192.168.1.19`.
- Pakiet `my_bot` (repo github.com/mjasic/my_bot, galaz main, remote SSH). Plugin ros2_control `diffdrive_arduino` (fork Josha Newansa, galaz humble) ma lokalny commit z winda; nie ma prawa push, lata jest w `my_bot/patches/diffdrive_arduino_lift.patch`.
- Auth do GitHub tylko przez SSH, uzytkownik nie chce sie logowac tokenami. Nie dopisuj Co-Authored-By do commitow.

## Dziala (potwierdzone na prawdziwym robocie)
- ESP32 (PID z feedforward, enkodery, serial `e`, `m L R`, `o`, `r`, `u`, `s`, `l <pwm>`), odometria, IMU+EKF, lidar RPLidar A1, SLAM, AMCL, Nav2 z `nav2_params_real.yaml` i mapa `maps/real_map2.yaml`.
- Winda (2 silowniki liniowe na MDD3A, piny ESP32 22/23): z pada os 7 przez `scripts/lift_joy.py` -> `/lift_cmd` (Int16) -> plugin. Timeout 500 ms. Wymaga `autorepeat_rate:=20.0` w joy_node (do dodania na stale w konfiguracji).
- Lidar nie kreci sie bez potrzeby: `scripts/lidar_toggle.py` (start gdy pojawi sie subskrybent /scan lub przytrzymanie przycisku 3 przez 1 s, stop po 2 s przytrzymania) + systemd `lidar-guard` (`/usr/local/bin/lidar_guard.py`) trzyma DTR zeby silnik nie startowal po zamknieciu portu.
- Kamera Pi Camera 3 (`launch/pi_cam.launch.py`): camera_ros, 640x480, 15 fps, jpeg_quality 40, orientation 180 (obraz prosto), AfMode 0 + LensPosition 1.5, apriltag_node (config/apriltag.yaml, tag36h11). `/detections` leci 15 Hz z opoznieniem ok. 0,033 s.
- Symulacja: docking dziala (DockRobot success), staging 1 m przed dokiem (staging_x_offset -1.0).

## WAZNE zasady dla kamery
- NIGDY nie subskrybuj `/camera/image_raw` zdalnie (z PC) - surowe 1,2 MB/klatke przez Wi-Fi dlawi wezel kamery (publikuje reliable) i opoznienie rosnie do ~1-1,5 s, a rate spada do 5 Hz. Lokalnie na Pi (apriltag) jest OK.
- Podglad na PC: `python3 ~/cam_view.py` (odbiera `/camera/image_raw/compressed` best effort, publikuje `/camera/image_view`), w RViz Image Topic `/camera/image_view`. `image_transport republish` w Jazzy nie dziala jak oczekiwano (ignoruje argumenty pozycyjne, wymaga parametrow in_transport/out_transport, u nas i tak nie podlaczalo sie).
- Nie ustawiaj qos_overrides best_effort na raw - apriltag subskrybuje reliable i przestaje dostawac klatki.
- Nav2 dockowanie wymaga swiezosci detekcji < external_detection_timeout (1.0 s).

## Docking na prawdziwym robocie (stan 2026-11-11)
Dziala: DockRobot z `navigate_to_staging_pose: false` z ok. 70 cm od taga - SUCCEEDED w 7 s, blad boczny 1 mm.
- Tag tag36h11 id 0, czarny kwadrat 80 mm, na wysokosci obiektywu. `config/apriltag.yaml`: `decimate: 2.0` (z 1.0 apriltag zjadal 77% rdzenia i przy przeciazonym Pi gubil detekcje).
- Kalibracja kamery (szachownica 9x6, pole 25 mm, rms 0.24 px): fx ~971, cx ~431. Przesuniety cx jest prawdziwy (sprawdzone tagiem na wprost obiektywu). HFOV tylko ok. 36 st.
- Kamera w URDF: x 0.265, z 0.055 od base_link (base_link = podloga pod osia kol), zmierzone linijka.
- `pi_cam.launch.py`: `frame_id: camera_link_optical` (domyslnie camera_ros daje `camera` i TF do taga nie powstaje) + `detected_dock_pose_publisher`. Uruchamiac `launch_robot.launch.py use_camera:=true`.
- `nav2_params_real.yaml` docking: home_dock `[-0.618, -0.063, -1.597]` (real_map2), `external_detection_translation_x: -0.53` (oś kol 53 cm od taga, obiektyw 27 cm - blizej tag nie miesci sie w kadrze), `staging_x_offset: -0.45` (za dockiem ok. 1 m do sciany), `docking_threshold: 0.03`, `max_retries: 0` (retry cofa na slepo do staging - robot walil w sciany), `use_collision_detection: true`.
- Nie dawac komentarzy z dwukropkiem w xacro - launch_robot parsuje robot_description jako YAML i sie wywala.

Do zrobienia: pelne dokowanie z nawigacja do staging z drugiego konca pokoju; ewentualnie stacja ladowania (use_battery_status).

## Znane drobiazgi
- W symulacji `max_angular_accel` powinno byc 2.5 (10.0 powodowalo telepanie przy przeciazonym PC); na prawdziwym robocie 10.0 jest OK. Sprawdz `grep max_angular_accel config/nav2_params*.yaml`.
- Telepanie przy obrocie w miejscu w sim bylo skutkiem przeciazenia PC (petla ~7,7 Hz), nie bledu parametrow.
- Pi nie ma RTC, czas z NTP.
