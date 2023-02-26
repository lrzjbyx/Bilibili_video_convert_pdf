import argparse
import os

from BilibiliVideoDownloader import BilibiliVideoDownloader
from VideoConvertPdf import VideoConvertPdf


def main(opt):
    path = opt.address
    if path == "":
        print("输入地址不合法")

    file_path = ""
    # 判断是否为网络链接
    if path[:8] =="http://" or path[:8] =="https://":
        # 下载视频
        d = BilibiliVideoDownloader(path,save_path=opt.target,cookie=opt.cookie)
        d.require_input_link_video()
        d.require_video_list()
        d.get_all_video_episodes()
        file_path = d.download_video(d.get_all_video_episodes())

    else:
        file_path = path

    file_list = os.listdir(file_path)
    file_list = [ file  for file in file_list if os.path.splitext(file)[-1] == '.mp4' ]

    if opt.pdf:
        print("转pdf开始！")
        for file_name in file_list:
            print("《{0}》开始转关键帧pdf！".format(file_name))
            v = VideoConvertPdf(os.path.join(file_path,file_name))
            v.convert()

        print("文件转换成功！")




if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--address', type=str,default=r"https://www.bilibili.com/video/BV1jA411m7WG/?spm_id_from=333.1007.tianma.1-3-3.click&vd_source=da046271f989b34b9f60f03f7a1a20be")
    parser.add_argument('--pdf', type=bool,default=True)
    parser.add_argument('--target', type=str, default = os.path.join(os.getcwd(), "bilibili"))
    parser.add_argument('--cookie', type=str,default="")
    opt = parser.parse_args()
    main(opt)

