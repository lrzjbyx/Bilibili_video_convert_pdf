import math
import time
from multiprocessing import cpu_count, Manager
import cv2
from multiprocessing import  Process
import os
import uuid as uu
from PIL import Image
from PyPDF2 import PdfFileMerger, PdfMerger

from ClipVideo import ClipVideo
import psutil
import gc
import shutil


def hist_compare(image1, image2):
    hist1 = cv2.calcHist([cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)], [0], None, [256], [0, 256])
    hist2 = cv2.calcHist([cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)], [0], None, [256], [0, 256])
    match1 = cv2.compareHist(hist1, hist2, cv2.HISTCMP_BHATTACHARYYA)
    match2 = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    match3 = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CHISQR)
    # print("巴氏距离: %s, 相关性: %s, 卡方: %s"%(match1, match2, match3))
    return (match1, match2, match3)


class VideoConvertPdfProcess(Process):

    def __init__(self,process_id,item,id_dict):
        super(VideoConvertPdfProcess,self).__init__()
        self.id = process_id
        self.video_thunk_path = item["path"]
        self.episodes = item["episodes"]
        self.index =  item["index"]
        self.root = os.path.join(item["root"],str(item["index"]))
        if not os.path.exists(self.root):
            os.mkdir(self.root)

        # 用来保存结果
        self.id_dict = id_dict

    def run(self):
        cap = cv2.VideoCapture(self.video_thunk_path)
        # 总 帧 数
        num_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        # 每秒帧率
        fps = cap.get(cv2.CAP_PROP_FPS)
        pre = None
        b = self.episodes[0]
        r = []
        c = 0
        j = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if c >= int(self.episodes[1]-self.episodes[0]) or not ret:
                break

            if ret and not pre is None:
                c += 1
                (match1, match2, match3) = hist_compare(frame, pre)
                if match2 < 0.95 or match1 > 0.1:
                    pre = frame.copy()
                    cv2.putText(frame, "{0}:{1}:{2}".format(int((c+b) / fps / 60), int((c+b) / fps) % 60, round((c+b) % fps, 4)),
                                (20, 50), cv2.FONT_HERSHEY_COMPLEX, 2.0, (100, 200, 200), 5)

                    filename = os.path.join(self.root,"{0}.png".format(j))
                    cv2.imwrite(filename,frame)
                    r.append(filename)
                    j+=1
                    # r.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            if pre is None:
                c += 1
                pre = frame
        self.id_dict[str(self.index)] = r
        # print(self.index)
        # print(self.id_dict)


class VideoConvertPdf():
    def __init__(self,video_path,save_path='./temp'):
        self.video_path = video_path
        # 文件名称
        self.file_name = os.path.splitext(self.video_path)[0]
        self.cpu_count = cpu_count()
        self.clip_video_path = None
        # 临时目录  使用完成会删除
        self.save_path = save_path+"/"+str(uu.uuid4())+"/"
        self.thunk_video = []

        pass

    def clip_video(self):

        # 创建目录
        if not os.path.exists(self.save_path):
            os.mkdir(self.save_path)
        # 裁剪视频
        clip = ClipVideo(self.video_path,self.save_path)
        success,points = clip()

        return success,points

    def merge_pdf(self,merge_list):
        frame = cv2.imread(merge_list[0])
        pic = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        mem = psutil.virtual_memory()
        max_all = round(mem.free*0.2 / 1024 / 1024)
        images = []
        i = 0
        j = 0
        l = len(merge_list)
        # 临时目录
        t =  os.path.join(os.path.join(os.getcwd(), "temp"), str(uu.uuid4()))
        if not os.path.exists(t):
            os.mkdir(t)
        while(i<l):
            while(max_all<round(mem.free / 1024 / 1024) and i<l ):
                image = Image.fromarray(cv2.cvtColor(cv2.imread(merge_list[i]), cv2.COLOR_BGR2RGB))
                images.append(image)
                i+=1

            if len(images) >0:
                images[0].save(os.path.join(t, "{0}.pdf".format(str(j))), save_all=True, append_images=images)
                j += 1


            for im in images:
                del im
            gc.collect()

            images = []

        merger = PdfMerger()
        for i in range(len(os.listdir(t))):
            # print(os.path.join(t,"{0}.pdf".format(i)))
            merger.append(os.path.join(t,"{0}.pdf".format(i)))

        merger.write(self.file_name+".pdf")
        merger.close()

        [os.remove(os.path.join(t,i)) for i in os.listdir(t)]
        os.rmdir(t)

    def convert(self):
        # 进程列表
        process_list = []
        # 结果集合
        result_dict = Manager().dict()

        success, points = self.clip_video()

        if success:
            # 读取视频文件
            clip_video_path = [ os.path.join(self.save_path,i) for i in os.listdir(self.save_path)]
            # 保存路径
            save_key_frame_root_path = os.path.join(os.path.join(os.getcwd(), "temp"), str(uu.uuid4()))
            if not os.path.exists(save_key_frame_root_path):
                os.mkdir(save_key_frame_root_path)

            # 视频块
            for i in range(len(clip_video_path)):
                item = {}
                # item["path"] = clip_video_path[i]
                item["path"] = os.path.join(self.save_path,"{0}.mp4".format(i))
                item["root"] = save_key_frame_root_path
                item["episodes"] = points[i]
                item["index"] = i
                self.thunk_video.append(item)
                # 初始化结果字典
                result_dict[str(i)] = []

            # 视频特征帧
            for i,item in enumerate(self.thunk_video):
                p = VideoConvertPdfProcess(i,item,result_dict)  # 实例化进程对象
                p.start()
                process_list.append(p)

            # 等待返回结果
            for p in process_list:
                p.join()

            # 合并特征帧
            merge_list = []
            # print(result_dict)

            # print(result_dict)
            for k,item in result_dict.items():
                merge_list.extend(item)


            # print(len(merge_list))

            self.merge_pdf(merge_list)
            # merge_list[0].save(self.file_name+".pdf", "pdf", save_all=True, append_images=merge_list)

            # 删除临时文件夹
            for i in range(len(clip_video_path)):
                os.remove(clip_video_path[i])
            os.rmdir(self.save_path)
            shutil.rmtree(save_key_frame_root_path, ignore_errors=True)




