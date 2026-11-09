"""Calibration CLI. The robot is NEVER driven by this tool.

floor --pairs describes ground x-forward/y-left in METRES and points picked
from an UNDISTORTED image if camera intrinsics are in use.
"""
import argparse
import glob
import json
from pathlib import Path
import cv2
import numpy as np


def intrinsic(images: list[str], nx: int, ny: int, square_m: float) -> dict:
    obj = np.zeros((nx*ny, 3), np.float32)
    obj[:,:2] = np.mgrid[0:nx,0:ny].T.reshape(-1,2) * square_m
    op, ip = [], []
    shape = None
    for fn in images:
        frame = cv2.imread(fn)
        if frame is None:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if shape is not None and shape != gray.shape:
            raise ValueError('All calibration images must have same dimensions')
        shape = gray.shape
        ok, corners = cv2.findChessboardCorners(gray, (nx,ny))
        if ok:
            refined = cv2.cornerSubPix(gray,corners,(11,11),(-1,-1),
                (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,30,0.001))
            op.append(obj)
            ip.append(refined)
    if len(op) < 8:
        raise ValueError(f'Only {len(op)} usable chessboards; need >=8 diverse images')
    rmse,K,D,_,_=cv2.calibrateCamera(op,ip,(shape[1],shape[0]),None,None)
    return {'camera_matrix':K.tolist(),'dist_coeffs':D.ravel().tolist(),
            'image_width':shape[1], 'image_height':shape[0],
            'intrinsic_reprojection_rmse_pixels':float(rmse), 'chessboards_used':len(op)}


def floor(pairs: dict, intr: dict | None = None) -> dict:
    # At least 4 non-collinear measured correspondences. Better use 6+ points.
    img = np.asarray(pairs['pixel_points'],np.float32)
    ground = np.asarray(pairs['ground_xy_m'],np.float32)
    if len(img)<4 or img.shape != ground.shape or img.shape[1] != 2:
        raise ValueError('Need >=4 matching pixel_points and ground_xy_m coordinates')
    H, inliers = cv2.findHomography(img,ground,method=0)
    if H is None or not np.isfinite(H).all():
        raise ValueError('Degenerate point set')
    pred = cv2.perspectiveTransform(img.reshape(-1,1,2),H).reshape(-1,2)
    fit_rmse = float(np.sqrt(np.mean(np.sum((pred-ground)**2, axis=1))))
    result = {
        'calibration_type':'real','validated':False,
        'camera_matrix':None if intr is None else intr['camera_matrix'],
        'dist_coeffs':None if intr is None else intr['dist_coeffs'],
        'homography_img_to_ground':H.tolist(),
        'floor_roi_pixels':pairs['floor_roi_pixels'],
        'image_width':int(pairs['image_width']),
        'image_height':int(pairs['image_height']),
        'ground_rmse_m':None,
        'fit_rmse_m_not_independent':fit_rmse,
        'notes':'Requires independent HOLDOUT points and validation before real drive.'
    }
    return result


def validate(data: dict, holdout: dict, rmse_max: float, mark: bool) -> dict:
    p=np.asarray(holdout['pixel_points'],np.float32)
    g=np.asarray(holdout['ground_xy_m'],np.float32)
    if len(p)<5 or p.shape!=g.shape or p.shape[1]!=2:
        raise ValueError('Need >=5 independently measured holdout points')
    H=np.asarray(data['homography_img_to_ground'],np.float64)
    pred=cv2.perspectiveTransform(p.reshape(-1,1,2),H).reshape(-1,2)
    errors=np.linalg.norm(pred-g,axis=1)
    rmse=float(np.sqrt(np.mean(errors**2)))
    data['ground_rmse_m']=rmse
    data['ground_max_error_m']=float(np.max(errors))
    data['holdout_count']=len(p)
    data['validated']=bool(mark and rmse<=rmse_max and data.get('calibration_type')=='real')
    return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    subs=parser.add_subparsers(dest='command',required=True)
    a=subs.add_parser('intrinsic')
    a.add_argument('--glob',required=True,help='quoted glob for checkerboard images')
    a.add_argument('--cols',type=int,default=8,help='internal corners along board width')
    a.add_argument('--rows',type=int,default=6)
    a.add_argument('--square-m',type=float,default=0.025)
    a.add_argument('--output',required=True)
    b=subs.add_parser('floor')
    b.add_argument('--pairs',required=True,help='JSON measured undistorted-pixel / ground points')
    b.add_argument('--intrinsics',help='intrinsic calibration JSON')
    b.add_argument('--output',required=True)
    c=subs.add_parser('validate')
    c.add_argument('--calibration',required=True)
    c.add_argument('--holdout',required=True)
    c.add_argument('--rmse-max-m',type=float,default=0.015)
    c.add_argument('--mark-valid',action='store_true',help='after independent physical measurements')
    c.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.command=='intrinsic':
        result=intrinsic(sorted(glob.glob(args.glob)),args.cols,args.rows,args.square_m)
    elif args.command=='floor':
        intr=None if args.intrinsics is None else json.loads(Path(args.intrinsics).read_text())
        result=floor(json.loads(Path(args.pairs).read_text()),intr)
    else:
        result=validate(json.loads(Path(args.calibration).read_text()),
            json.loads(Path(args.holdout).read_text()),args.rmse_max_m,args.mark_valid)
    Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Saved:',args.output,'validated=',result.get('validated'),'RMSE=',
          result.get('ground_rmse_m', result.get('intrinsic_reprojection_rmse_pixels')))


if __name__=='__main__':
    main()
