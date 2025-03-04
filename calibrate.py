#!/usr/bin/env python
import argparse
import os
import pickle
from glob import glob

import cv2
import numpy as np
import yaml

def main(input, output,
         pattern_size=(7, 4),
         debug_dir=None,
         corners_f=None,
         framestep=20,
         max_frames=None,
         **_):

    if '*' in input:
        source = glob(input)
    else:
        source = cv2.VideoCapture(input)

    pattern_points = np.zeros((np.prod(pattern_size), 3), np.float32)
    pattern_points[:, :2] = np.indices(pattern_size).T.reshape(-1, 2)

    obj_points = []
    img_points = []
    h, w = 0, 0
    frame = -1
    used_frames = 0
    while True:
        frame += 1
        if isinstance(source, list):
            # glob
            if frame == len(source):
                break
            img = cv2.imread(source[frame])
        else:
            # cv2.VideoCapture
            retval, img = source.read()
            if not retval:
                break
            if frame % framestep != 0:
                continue

        print(f'Searching for chessboard in frame {frame}... ', end='')
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = img.shape[:2]
        found, corners = cv2.findChessboardCorners(img, pattern_size, flags=cv2.CALIB_CB_FILTER_QUADS)
        if found:
            term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 30, 0.1)
            cv2.cornerSubPix(img, corners, (5, 5), (-1, -1), term)
            used_frames += 1
            img_points.append(corners.reshape(1, -1, 2))
            obj_points.append(pattern_points.reshape(1, -1, 3))
            print('ok')
            if max_frames is not None and used_frames >= max_frames:
                print(f'Found {used_frames} frames with the chessboard.')
                break
        else:
            print('not found')

        if debug_dir is not None:
            img_chess = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            cv2.drawChessboardCorners(img_chess, pattern_size, corners, found)
            cv2.imwrite(os.path.join(debug_dir, '%04d.png' % frame), img_chess)

    if corners_f is not None:
        with open(corners_f, 'wb') as fw:
            pickle.dump(img_points, fw)
            pickle.dump(obj_points, fw)
            pickle.dump((w, h), fw)

# load corners
#    with open('corners.pkl', 'rb') as fr:
#        img_points = pickle.load(fr)
#        obj_points = pickle.load(fr)
#        w, h = pickle.load(fr)

    print('\ncalibrating...')
    rms, camera_matrix, dist_coefs, rvecs, tvecs = cv2.calibrateCamera(obj_points, img_points, (w, h), None, None)
    print("RMS:", rms)
    print("camera matrix:\n", camera_matrix)
    print("distortion coefficients: ", dist_coefs.ravel())

    # # fisheye calibration
    # rms, camera_matrix, dist_coefs, rvecs, tvecs = cv2.fisheye.calibrate(
    #     obj_points, img_points,
    #     (w, h), camera_matrix, np.array([0., 0., 0., 0.]),
    #     None, None,
    #     cv2.fisheye.CALIB_USE_INTRINSIC_GUESS, (3, 1, 1e-6))
    # print "RMS:", rms
    # print "camera matrix:\n", camera_matrix
    # print "distortion coefficients: ", dist_coefs.ravel()

    calibration = {'rms': rms, 'camera_matrix': camera_matrix.tolist(), 'dist_coefs': dist_coefs.tolist()}
    with open(output, 'w') as fw:
        yaml.dump(calibration, fw)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calibrate camera using a video of a chessboard or a sequence of images.')
    parser.add_argument('input', help='input video file or glob mask')
    parser.add_argument('output', help='output calibration yaml file')
    parser.add_argument('--pattern_size', '-ps', nargs=2, help='pattern grid size (nb colums, nb rows)', default=[7, 4], type=int)
    parser.add_argument('--debug-dir', help='path to directory where images with detected chessboard will be written',
                        default=None)
    parser.add_argument('-c', '--corners_f', help='output corners file', default=None)
    parser.add_argument('-fs', '--framestep', help='use every nth frame in the video', default=20, type=int)
    parser.add_argument('-max', '--max-frames', help='limit the number of frames used for calibration', default=None, type=int)
    args = parser.parse_args()

    main(**vars(args))
    print('exiting')
