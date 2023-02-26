import math
from multiprocessing import cpu_count
import cv2
from multiprocessing import  Process
import os


def clip_process_task(video_path, begin_frame_points, end_frame_points, process_id,vide_save_path):
    cap = cv2.VideoCapture(video_path)
    cap.set(1, begin_frame_points)
    fps = cap.get(cv2.CAP_PROP_FPS)
    dist = end_frame_points - begin_frame_points
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    output = cv2.VideoWriter(vide_save_path+'/{}.mp4'.format(process_id), fourcc, int(fps),
                             (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))
    c = 0
    while cap.isOpened():
        success, frame = cap.read()
        if success and c <= dist:
            output.write(frame)
        else:
            break
        c += 1

    # print("线程{0}完成切割".format(process_id))



class ClipVideo():
    def __init__(self,video_path,vide_save_path):
        # CPU 个数
        self.cpu_count = int(cpu_count()/2)
        # 视频保存路径
        self.vide_save_path = vide_save_path
        # 视频读取路径
        self.video_path = video_path
        # 视频文件读取
        self.cap = cv2.VideoCapture(self.video_path)
        # 每秒帧率
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        # 总共帧数
        self.num_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
        print("总共帧数{0},每秒帧率{1}".format(self.num_frames,self.fps))
        # 高度
        self.frame_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        # 宽度
        self.frame_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)



        if self.cpu_count >= 2:
            # 每个视频块帧数大小
            self.sheet_size_b = math.ceil(self.num_frames / self.cpu_count)
            # 最后一个视频块帧大小
            self.sheet_size_a = self.num_frames - (self.sheet_size_b * self.cpu_count-1)
        else:
            self.sheet_size_b = self.num_frames

            self.sheet_size_a = 0


    def __call__(self, *args, **kwargs):
        clip_task_points = []
        process_list = []
        for i in range(self.cpu_count-1):
            clip_task_points.append((self.sheet_size_b * i,self.sheet_size_b*(i+1)-1))

        clip_task_points.append((self.sheet_size_b*(self.cpu_count-1),int(self.num_frames-1)))

        for i in range(len(clip_task_points)):
            p = Process(target=clip_process_task, args=(self.video_path,clip_task_points[i][0],clip_task_points[i][1],i,self.vide_save_path))  # 实例化进程对象
            p.start()
            process_list.append(p)

        for p in process_list:
            p.join()


        # 视频切割点
        # print(clip_task_points)
        return True,clip_task_points


# if __name__ == '__main__':
#     clip = ClipVideo("123.flv","123")
#     clip()