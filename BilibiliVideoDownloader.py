import os
import sys
from copy import copy
import requests, time, hashlib, urllib.request, re, json
from lxml import etree
from urllib.parse import urljoin, urlparse
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.io.VideoFileClip import VideoFileClip
import uuid
import ffmpeg
from progress import bar
from progressbar import progressbar

'''
        支持如下视频格式  https://github.com/leiurayer/downkyi
        # - [x] av号：av170001，https://www.bilibili.com/video/av170001
        # - [x] BV号：BV17x411w7KC，https://www.bilibili.com/video/BV17x411w7KC, https://b23.tv/BV17x411w7KC


        思路
        # - [x] 获取视频信息的链接
            #   https://api.bilibili.com/x/web-interface/view?bvid=BV18B4y1x7Rs
            #   https://api.bilibili.com/x/web-interface/view?aid=170001


        # - [x] 获取分级视频的链接
            # 在获取视频链接时会返回JSON，数据中包含pages字段和bvid键值
                {
                    "cid": 11111111,
                    "page": 1,
                    "from": "vupload",
                    "part": "1. xxxx-1",
                    "duration": 615,
                    "vid": "",
                    "weblink": "",
                    "dimension": { "width": 1280, "height": 720, "rotate": 0 },
                    "first_frame": "http://i0.hdslbxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                }
            # 拼接分集视频的链接
                https://api.bilibili.com/x/player/playurl?cid={0}&qn=125&fourk=1&fnver=0&fnval=4048&bvid={1}
                cid     11111111
                bvid    BV18B4y1x7Rs
        # - [x] 获取每个视频真正的播放地址
            # 视频支持格式和清晰度["support_formats"]
            # 视频链接["video"]
                # id 代表不同的视频清晰度         ["16","32","64",...]
            # 音频链接["audio"]
                # id 代表不同的音频编码方式        ["30216","30232","30280"]

        # -[x] 下载视频      
        # -[x] 拼接视频音频


'''


class BilibiliVideoDownloader():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
        # 'referer': 'https://www.bilibili.com/'
    }
    audio_quality = {
        "30216": "64K",
        "30232": "132K",
        "30280": "192K"
    }
    video_quality = {
        "16": "360P 流畅",
        "32": "480P 清晰",
        "64": "720P 高清",
        "74": "720P 60帧",
        "80": "1080P 高清",
        "112": "1080P 高码率"
    }

    '''
    @:param video_url   视频链接
    @:param save_path   视频位置
    '''

    def __init__(self, video_url, save_path=os.path.join(os.getcwd(), "bilibili")):
        # 下载临时目录
        self.save_temporary_doc = os.path.join(os.getcwd(), "temp")
        # 保存路径
        self.save_path = save_path
        # 请求视频链接
        self.video_url = video_url
        # 视频详解
        self.video_detailed = None
        # 多个p
        self.video_episodes_abridge = None
        # 视频详情
        self.video_detailed_base_url = "https://api.bilibili.com/x/web-interface/view?"
        # bv 链接
        self.av_bv_base_url = [
            "https://www.bilibili.com/video/", "https://b23.tv/"
        ]
        self.bvid = None
        self.aid = None
        # 初始化
        self.video_id()
        # 每个视频的详细信息
        self.every_video_detailed = {}
        # 每个视频的详细信息
        self.every_video_detailed_url = "https://api.bilibili.com/x/player/playurl?cid={0}&qn=125&fourk=1&fnver=0&fnval=4048&bvid={1}"

        # 初始化下载器
        self.opener = urllib.request.build_opener()

        self.opener.addheaders = [
            # ('Host', 'upos-hz-mirrorks3.acgvideo.com'),  #注意修改host,不用也行
            ('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:56.0) Gecko/20100101 Firefox/56.0'),
            ('Accept', '*/*'),
            ('Accept-Language', 'en-US,en;q=0.5'),
            ('Accept-Encoding', 'gzip, deflate, br'),
            ('Range', 'bytes=0-'),  # Range 的值要为 bytes=0- 才能下载完整视频
            ('Referer', "https://www.bilibili.com"),  # 注意修改referer,必须要加的!
            ('Origin', 'https://www.bilibili.com'),
            ('Connection', 'keep-alive'),
        ]
        urllib.request.install_opener(self.opener)

    def BvAv(self, t):
        # AV BV

        t = urljoin(t, urlparse(t).path)

        if t[0: len(self.av_bv_base_url[1])] == self.av_bv_base_url[1]:
            return t[len(self.av_bv_base_url[1]):].split("/")[0]
        elif t[0: len(self.av_bv_base_url[0])] == self.av_bv_base_url[0]:
            return t[len(self.av_bv_base_url[0]):].split("/")[0]
        else:
            return None

    def video_id(self):
        bv_av = self.BvAv(self.video_url + "/")
        if bv_av is None:
            return

        if bv_av[:2].lower() == "bv":
            self.bvid = bv_av
        else:
            self.aid = bv_av[2:]

    def require_video_detailed(self, url):

        response = requests.get(url, headers=BilibiliVideoDownloader.headers)
        video_detailed = json.loads(response.content.decode("utf-8"))

        return video_detailed

    def require_input_link_video(self):
        url = ""

        if self.aid is None:
            url = self.video_detailed_base_url + "bvid=" + self.bvid
        else:
            url = self.video_detailed_base_url + "aid=" + self.aid

        self.video_detailed = self.require_video_detailed(url)

        print(self.video_detailed)

        self.save_path = os.path.join(self.save_path, "".join(
            re.findall('[\u4e00-\u9fa5a-zA-Z0-9]+', self.video_detailed["data"]["title"], re.S)))

        # 创建目录
        if not os.path.exists(self.save_path):
            os.mkdir(self.save_path)

        self.video_episodes_abridge = self.video_detailed["data"]["pages"]
        self.bvid = self.video_detailed["data"]["bvid"]
        self.aid = self.video_detailed["data"]["aid"]

        return self.video_detailed

    def require_video_list(self):

        items = []

        for video_eppisode in self.video_episodes_abridge:
            response = requests.get(self.every_video_detailed_url.format(video_eppisode["cid"], self.bvid),
                                    headers=BilibiliVideoDownloader.headers)
            t = json.loads(response.content.decode("utf-8"))
            self.every_video_detailed[str(video_eppisode["cid"])] = t

            if len(self.video_episodes_abridge) == 1:
                title = self.video_detailed["data"]["title"]
            else:
                title = video_eppisode["part"]

            item = {
                "cid": video_eppisode["cid"],
                "title": title,
                "audio_quality": [a["id"] for a in t["data"]["dash"]["audio"]],
                "video_quality": t["data"]["support_formats"],
            }
            print(item)

            items.append(item)

        return items

    '''
    @:param download_item_list {
        "cid":"视频cid号   int"
        "audio_quality":"音频质量   int"
        "video_quality":"视频质量   int"
        "video_codecs":" 视频编码   str"
    }

    '''

    def download_video(self, download_item_list):

        # download_item_list = [{"cid": "804547522", "audio_quality": "30280", "video_quality": "64",
        #                        "video_codecs": "hev1.1.6.L120.90"}]

        for download_item in download_item_list:
            video_uuid = str(uuid.uuid4())

            video_uuid_path = os.path.join(self.save_temporary_doc, video_uuid + ".video")
            audio_uuid_path = os.path.join(self.save_temporary_doc, video_uuid + ".audio")

            video_title = [v["part"] for v in self.video_episodes_abridge if v["cid"] == int(download_item["cid"])][0]

            if len(self.video_episodes_abridge) == 1:
                video_title = self.video_detailed["data"]["title"]

            # 下载视频
            video_item = [v for v in self.every_video_detailed[download_item["cid"]]["data"]["dash"]["video"] if
                          v["id"] == int(download_item["video_quality"])]
            if len(video_item) == 0:
                return

            for i, video_url in enumerate(
                    [item["baseUrl"] for item in video_item if item["codecs"] == download_item["video_codecs"]]):
                urllib.request.urlretrieve(url=video_url, filename=video_uuid_path)

            # 下载音频
            audio_quality = int(download_item["audio_quality"])

            audio_item = [a for a in self.every_video_detailed[download_item["cid"]]["data"]["dash"]["audio"] if
                          a["id"] == audio_quality]

            for i, video_url in enumerate([item["baseUrl"] for item in audio_item]):
                urllib.request.urlretrieve(url=video_url, filename=audio_uuid_path)

            if self.combining_video_audio(video_uuid_path, audio_uuid_path, video_title):
                os.remove(video_uuid_path)
                os.remove(audio_uuid_path)
                print("{0}视频下载完成".format(video_title))

        return self.save_path

    def get_all_video_episodes(self):

        items = []
        for one_video_detailed_key in self.every_video_detailed.keys():
            item = {}
            max_quality = (80 if max([o["quality"] for o in self.every_video_detailed[one_video_detailed_key]["data"][
                "support_formats"]]) > 80 else max(
                [o["quality"] for o in self.every_video_detailed[one_video_detailed_key]["data"]["support_formats"]]))

            item["cid"] = one_video_detailed_key
            item["video_quality"] = max_quality
            item["audio_quality"] = max(
                [a["id"] for a in self.every_video_detailed[one_video_detailed_key]["data"]["dash"]["audio"]])
            item["video_codecs"] = \
                [v["codecs"] for v in self.every_video_detailed[one_video_detailed_key]["data"]["support_formats"] if
                 v["quality"] == max_quality][0][0]
            items.append(item)

        return items

    def combining_video_audio(self, video_uuid_path, audio_uuid_path, video_title):
        try:

            # 合并视频
            '''
                合并视频方式一
                @   优点：满足需求
                @   缺点：速度太慢
            '''
            # video_clip = VideoFileClip(video_uuid_path)
            # audio_clip = AudioFileClip(audio_uuid_path)
            # video_clip = video_clip.set_audio(audio_clip)
            # video_clip.to_videofile(r'{}.mp4'.format(os.path.join(self.save_path,video_title)), fps=30,remove_temp=True)

            # 合并视频
            '''
                合并视频方式二
                @   优点：满足需求 速度稍微变快
                @   缺点：方式一的多进程版本
            '''
            video_stream = ffmpeg.input(video_uuid_path)
            audio_stream = ffmpeg.input(audio_uuid_path)
            output_stream = ffmpeg.output(audio_stream, video_stream,
                                          r'{}.mp4'.format(os.path.join(self.save_path, video_title)))
            stream = ffmpeg.overwrite_output(output_stream)
            ffmpeg.run(stream)
            return True
        except:
            return False


# # d = BilibiliVideoDownloader("https://www.bilibili.com/video/BV1aB4y1B75E/?spm_id_from=333.788.recommend_more_video.4&vd_source=c60a8cff7283d8fe87cf05ce442b3759")
# # d = BilibiliVideoDownloader("https://www.bilibili.com/video/BV1n54y1i7VZ?spm_id_from=333.337.search-card.all.click")
# d = BilibiliVideoDownloader("https://www.bilibili.com/video/BV1DU4y1q72G?spm_id_from=333.851.b_7265636f6d6d656e64.1")
# # d = BilibiliVideoDownloader("https://www.bilibili.com/video/av170001")
# # d =  BilibiliVideoDownloader("https://b23.tv/BV17x411w7KC")
# # d = BilibiliVideoDownloader("https://www.bilibili.com/video/BV15w411Z7LG?spm_id_from=333.337.search-card.all.click")
#
# d.require_input_link_video()
# d.require_video_list()
# d.get_all_video_episodes()
# d.download_video(d.get_all_video_episodes())
