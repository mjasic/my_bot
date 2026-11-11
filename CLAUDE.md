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

## Uruchamianie prawdziwego robota (Pi)
1. `ros2 launch my_bot launch_robot.launch.py use_camera:=true`
2. `ros2 launch my_bot nav_real.launch.py` (AMCL + map_server na real_map2 + Nav2, bond_timeout 10 s) i w ciagu ~60 s "2D Pose Estimate" w RViz, inaczej global_costmap nie wstanie.
3. Dokowanie: `ros2 action send_goal /dock_robot nav2_msgs/action/DockRobot "{use_dock_id: true, dock_id: home_dock, navigate_to_staging_pose: true}"` - uruchamiac NA PI (nie z PC), wtedy zerwane Wi-Fi nie przerywa dokowania.
- Na PC: RViz `config/nav.rviz`, pad: `ros2 run joy joy_node --ros-args --params-file config/joystick.yaml` + `ros2 run teleop_twist_joy teleop_node` (remap /cmd_vel -> /cmd_vel_joy). NIE `joystick.launch.py` - startuje drugi twist_mux.
- Pad idzie przez Wi-Fi: przy zerwanym Wi-Fi robota nie da sie zatrzymac padem (twist_mux sam zatrzymuje po 0.5 s braku komend). Do rozwazenia: dongle pada w Pi.
- Wi-Fi Pi: power save wylaczony (nmcli 802-11-wireless.powersave 2) - z wlaczonym lacze zrywalo sie na dziesiatki sekund.
- Pi bez RTC: po starcie poczekac na `timedatectl` "System clock synchronized: yes" (ok. 1 min), inaczej TF na PC sie rozjezdza.

## Docking na prawdziwym robocie (stan 2026-11-11)
Dziala pelne dokowanie z Nav2: z 1.6-1.9 m w 20-27 s, dokladnosc ok. 1 cm w odleglosci, 1-2 cm w bok.
Poprawki Nav2 w `nav2_params_real.yaml` potrzebne do tego: `rotate_to_goal_heading: true` (bez tego oscylacje przy obrocie przed dockiem), `default_server_timeout: 200` (20 ms - planner nie zdazal potwierdzic celu na Pi, robot stal mimo zaplanowanej sciezki), `PoseProgressChecker` (obrot w miejscu liczy sie jako postep).
- Tag tag36h11 id 0, czarny kwadrat 80 mm, na wysokosci obiektywu. `config/apriltag.yaml`: `decimate: 2.0` (z 1.0 apriltag zjadal 77% rdzenia i przy przeciazonym Pi gubil detekcje).
- Kamera: `sensor_mode 2304:1296` (pelna matryca), 768x432, HFOV 67.5 st. (wczesniej 640x480 z trybu 1536x864 = tylko 36 st. i tag wypadal z kadru przy korekcie). Kalibracja szachownica 9x6/25 mm, rms 0.19 px, fx ~574.
- Ekspozycja stala 8 ms (`ExposureTimeMode 1`, `ExposureTime 8000`, gain auto): przy auto ekspozycji w obrocie 0.3 rad/s tag byl wykrywany w 3-6/18 klatek, z 8 ms 18/18.

- Kamera w URDF: x 0.265, z 0.055 od base_link (base_link = podloga pod osia kol), zmierzone linijka.
- `pi_cam.launch.py`: `frame_id: camera_link_optical` (domyslnie camera_ros daje `camera` i TF do taga nie powstaje) + `detected_dock_pose_publisher`. Uruchamiac `launch_robot.launch.py use_camera:=true`.
- `nav2_params_real.yaml` docking: home_dock `[-0.618, -0.063, -1.597]` (real_map2), `external_detection_translation_x: -0.53` (oś kol 53 cm od taga, obiektyw 27 cm - blizej tag nie miesci sie w kadrze), `staging_x_offset: -0.45` (za dockiem ok. 1 m do sciany), `docking_threshold: 0.03`, `max_retries: 0` (retry cofa na slepo do staging - robot walil w sciany), `use_collision_detection: true`.
- Nie dawac komentarzy z dwukropkiem w xacro - launch_robot parsuje robot_description jako YAML i sie wywala.

Do zrobienia: pelne dokowanie z nawigacja do staging z drugiego konca pokoju; ewentualnie stacja ladowania (use_battery_status).

## Znane drobiazgi
- IMU MPU-6500 na I2C (Pi piny 1 3.3V, 3 SDA, 5 SCL, 6 GND, adres 0x68). NCS musi byc podpiety do 3.3 V, inaczej IMU nie pojawia sie na I2C. Luzny kabel IMU = smieciowy zyroskop w EKF = AMCL sie gubi (2026-11-11). Diagnoza: `i2cdetect -y 1`, w logu "Blad odczytu I2C". Po ponownym podlaczeniu zrestartowac wezel IMU (kalibracja zyroskopu, robot nieruchomo).
- W symulacji `max_angular_accel` powinno byc 2.5 (10.0 powodowalo telepanie przy przeciazonym PC); na prawdziwym robocie 10.0 jest OK. Sprawdz `grep max_angular_accel config/nav2_params*.yaml`.
- Telepanie przy obrocie w miejscu w sim bylo skutkiem przeciazenia PC (petla ~7,7 Hz), nie bledu parametrow.
- Pi nie ma RTC, czas z NTP.
