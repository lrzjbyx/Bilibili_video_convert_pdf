import argparse
import os

from BilibiliVideoDownloader import BilibiliVideoDownloader
from VideoConvertPdf import VideoConvertPdf

def main(path):
    file_path = ""
    # 判断是否为网络链接
    if path[:8] =="http://" or path[:8] =="https://":
        # 下载视频
        d = BilibiliVideoDownloader(path)
        d.require_input_link_video()
        d.require_video_list()
        d.get_all_video_episodes()
        file_path = d.download_video(d.get_all_video_episodes())

    else:
        file_path = path

    file_list = os.listdir(file_path)
    file_list = [ file  for file in file_list if os.path.splitext(file)[-1] == '.mp4' ]

    print("转pdf开始！")
    for file_name in file_list:
        print("《{0}》开始转关键帧pdf！".format(file_name))
        v = VideoConvertPdf(os.path.join(file_path,file_name))
        v.convert()

    print("文件转换成功！")




if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--address', type=str)
    opt = parser.parse_args()
    if opt.address == "":
        print("输入地址不合法")
    main(opt.address)

    # main("https://www.bilibili.com/video/BV19d4y197NK?spm_id_from=333.851.b_7265636f6d6d656e64.7&vd_source=c60a8cff7283d8fe87cf05ce442b3759")
    # print(os.path.splitext(file)[-1])
    # main(r"D:\Code\Python\Bilibili_video_convert_pdf\bilibili\朋友们没想到我居然要解释这种事情")