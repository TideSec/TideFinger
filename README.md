<div align=center><img src=images/logo.png width=30% ></div>


# TideFinger

TideFinger，一个开源的指纹识别小工具，使用了传统和现代检测技术相结合的指纹检测方法，让指纹检测更快捷、准确。

# 前言

通过分析web指纹的检测对象、检测方法、检测原理及常用工具，设计了一个简易的指纹搜集脚本来协助发现新指纹，并提取了多个开源指纹识别工具的规则库并进行了规则重组，开发了一个简单快捷的指纹识别小工具TideFinger，并实现了一套在线的指纹识别平台“潮汐指纹” [http://finger.tidesec.com](http://finger.tidesec.com)，希望能为大家带来方便。

通过对各种识别对象、识别方法、识别工具的分析，发现大家的指纹库各式各样，识别方式也是各有千秋，传统的md5、url路径的方式居多，识别header信息的也是不少，但没有一个能集众家之长的小工具和指纹库。

于是我们参考了webfinger和whatcms的部分代码并进行了整合优化，做了一个小工具TideFinger。

```
https://github.com/TideSec/TideFinger
```

**另外，我会不定期更新指纹库，关注我们最下方公众号，回复“指纹库”即可获取最新的的指纹库。**

我把指纹识别相关的一些原理、工具汇总成了一篇文章，详见[《Web指纹识别技术研究与优化实现》](https://github.com/TideSec/TideFinger/blob/master/Web%E6%8C%87%E7%BA%B9%E8%AF%86%E5%88%AB%E6%8A%80%E6%9C%AF%E7%A0%94%E7%A9%B6%E4%B8%8E%E4%BC%98%E5%8C%96%E5%AE%9E%E7%8E%B0.md)。

# 安装使用

## python3版

python3版加入了`Wappalyzer`的调用，并对结果进行了去重，同时加了目录匹配式选项，默认不会进行目录匹配方式的探测，因为这样会向目标系统发起大量的http请求。

1、识别脚本的安装和使用都比较简单。

安装python3依赖库
```
pip3 install -r requirements.txt  -i https://mirrors.aliyun.com/pypi/simple/

说明：sqlite3库在Python3 以上版本默认自带了该模块，如提示sqlite3出错请自行排查。
```

2、执行脚本
```
$ python3 TideFinger.py

    Usage: python3 TideFinger.py -u http://www.123.com [-p 1] [-m 50] [-t 5] [-d 0]

    -u: 待检测目标URL地址
    -p: 指定该选项为1后，说明启用代理检测，请确保代理文件名为proxys_ips.txt,每行一条代理，格式如: 124.225.223.101:80
    -m: 指纹匹配的线程数，不指定时默认为50
    -t: 网站响应超时时间，默认为5秒
    -d: 是否启用目录匹配式指纹探测（会对目标站点发起大量请求），0为不启用，1为启用，默认为不启用。
```

指纹识别界面如下：

<img src=images/025.png >

## python2版

1、识别脚本的安装和使用都比较简单。

安装python2依赖库
```
pip install -r requirements.txt  -i https://mirrors.aliyun.com/pypi/simple/

说明：sqlite3库在Python 2.5.x 以上版本默认自带了该模块，如提示sqlite3出错请自行排查。
```

2、执行脚本
```
$ python TideFinger.py

    Usage: python TideFinger.py -u http://www.123.com [-p 1] [-m 50] [-t 5]

    -u: 待检测目标URL地址
    -p: 指定该选项为1后，说明启用代理检测，请确保代理文件名为proxys_ips.txt,每行一条代理，格式如: 124.225.223.101:80
    -m: 指纹匹配的线程数，不指定时默认为50
    -t: 网站响应超时时间，默认为5秒
```

指纹识别界面如下：
<img src=images/022.png >

# 升级完善（2021.08）

## 主要完善功能点

1、**完成了python3的代码升级**。之前使用python2实现的，现在github里包含了python2和python3两个版本，可以根据自己环境去选。

2、**升级了tidefinger的自身指纹库**，2020年的时候指纹大约为2100条，目前指纹文件`cms_finger.db`已包含大约5900条指纹。

3、**引入了Wappalyzer指纹库**，使用了python版的Wappalyzer，代码来自`https://github.com/chorsley/python-Wappalyzer`。

4、**引入了`webanalyzer`指纹库**，这个是国内一群安全爱好者做的一个很不错的项目，项目地址`https://github.com/webanalyzer/`，里面的role也集成了WhatWeb、Wappalyzer、fofa的规则等。

5、因为多个指纹库都会有部分重合，所以后面对识别到的指纹进行了简单的去重处理，并对部分常见的误报进行了优化。

6、py2版本中在无法识别到cms时会默认使用数据库文件遍历的方式进行进一步指纹识别，但这样会对目标站点发起大量请求，我现在已经基本不大用这种方式，所以py3版加了个-d的选项，0为不启用，1为启用，默认为不启用。

## 新旧版本对比

**python2版：**

<img src=images/16294255548257.jpg >

<img src=images/16294255369065.jpg >

<img src=images/16294255091237.jpg >

**python3新版：**

<img src=images/16294257386932.jpg >

<img src=images/16294257808047.jpg >

<img src=images/16294258223684.jpg >

python3新版本获取的指纹更多，默认对目标发送大约4-5个数据包，而且都是没有攻击特征的，相对来说还是是可以接受的。

<img src=images/16294279226025.jpg >

<img src=images/16294279658552.jpg >

不大习惯自动化更新，所以指纹需要手动更新。

`Wappalyzer`指纹库的更新:`https://raw.githubusercontent.com/AliasIO/wappalyzer/master/src/technologies.json`，替换为对应的`technologies.json`文件即可。

`webanalyzer`指纹库的更新，指纹库`https://github.com/webanalyzer/rules`，替换到对应的`webanalyzer/rules`目录即可。

# 技术原理及实现

## 指纹库整理

我们搜集了大量的开源指纹识别工具，从中提取了指纹库，进行了统一的格式化处理并进行去重，最终得到了一个大约2078条的传统指纹库。本来想把fofa的库也合并进来，发现格式差异有些大，便保持了fofa指纹库，并把WebEye的部分指纹和fofa指纹进行了合并。这样就保留了两个指纹库，其中cms指纹库为传统的md5、url库，大约2078条指纹，可通过关键字、md5、正则进行匹配，fofa库为2119指纹，主要对Header、url信息进行匹配。

<img src=images/020.png >

## 指纹库优化

在对指纹库整理去重后，对每个指纹进行了命中率的标识，当匹配到某个指纹时该指纹命中率会加1，而在使用指纹时会从优先使用命中率高的指纹。

然后我们从互联网中爬取了10W个域名进行了命中率测试，然后对一些误报率比较高的指纹进行了重新优化，得到了一份相对更高效的指纹库。

<img src=images/024.png >


## 未知指纹发现

目前新指纹的识别基本还是靠人工发现然后分析规则再进行添加，所以各平台都有提交指纹的功能，但是我们没有这种资源，只能另想办法。

于是想到了一个比较笨的方法：从网站中爬取一些静态文件，如png、ico、jpg、css、js等，提取url地址、文件名、计算md5写入数据库，这样再爬下一个网站，一旦发现有相同的md5，就把新的url也加入到那条记录中，并把hint值加1，这样爬取10W个站点后，就能得到一个比较客观的不同网站使用相同md5文件的数据了。

有兴趣的可以查看具体代码`https://github.com/TideSec/TideFinger/blob/master/python2/count_file_md5.py`文件。

爬取的结果如下：

<img src=images/021.png >


当然了，里面肯定很多都属于误报，比如上图中第一个其实是个500错误页面，所以出现的比较多，第二个是政府网站最下边那个常见的“纠错”的js，所以用的也比较多...

经过一些分析整理也发现了一些小众的CMS和建站系统的指纹，比如三一网络建站系统的`newsxx.php`，比如大汉JCM的`jhelper_tool_style.css`等等，后续会持续把这些新的指纹丰富到指纹库中去。


## 指纹识别脚本

有了指纹库之后，识别脚本就相对比较简单了，已有的一些也都比较成熟了，直接使用了webfinger和whatcms的部分代码并进行了整合优化，于是就有了TideFinger。

1、功能逻辑都比较简单，先用fofa库去匹配，然后获取一定banner，如果banner中识别除了cms，则返回结果，如果未识别到cms，则会调用cms规则库进行匹配各规则。

2、脚本支持代理模式，当设置了-p参数，且`proxys_ips.txt`文件包含代理地址时，脚本会随机调用代理地址进行扫描，以避免被封ip，不过这样的话效率可能会低一些。毕竟搜集的免费代理质量还是差一些，速度会慢很多。有钱人可以找收费代理池，然后每个规则都用不同代理去请求，这样肯定不会被封！

代理地址的搜集可以使用我修改的另一个代理池`https://github.com/TideSec/Proxy_Pool`，提供了自动化的代理ip抓取+评估+存储+展示+接口调用。

3、经测试，一般网站把所有指纹跑一遍大约需要30秒时间，个别的网站响应比较慢的可能耗时更长一些，可以通过设置网站超时时间进行控制。


# 指纹识别平台

在有了指纹库和识别脚本之后，我们想继续完善下这个功能，于是又加入了其他一些功能，有个这个在线指纹查询平台`http://finger.tidesec.net`。

开始想加的很多，但后来在速度和时间方面不得不进行了一定的取舍，于是就有了目前如下的功能。

1、网站信息：网站标题、状态码、302跳转信息等；

2、IP地址信息：IP归属地、IP服务商信息、GPS信息；

3、CDN识别：对目标是否使用CDN进行检测，但目前CDN识别指纹还不多，对部分识别出使用CDN的目标还会列出来CNAME；

4、中间件识别：主要通过http头信息中的XPB、server等字段获取中间件信息，如nginx、iis、tomcat等；

5、更多banner：主要是调用了whatweb和Wapplyzer进行更多banner信息的获取，如jquery、bootstrap等；

6、操作系统识别：识别比较简单，通过ttl值和文件大小写是否敏感...用nmap去识别的话速度太慢...

7、本来还加入了子域名发现、端口扫描和waf探测等等，但发现耗时相对较长，而且比较容易被封IP，所以又去掉了。

团队没有专门做前端的，看云悉界面比较美观，所以就参考了云悉和WTF_Scan的界面布局，大佬不要打我们...使用了TP5框架，因为平台的功能都比较low，以防被喷就不放源码了。

大家可以试用下，给我们提提意见`http://finger.tidesec.net`

注册需要验证码，关注下我们公众号回复“潮汐指纹”即可~~被逼拉流量O(∩_∩)O哈哈~~

<img src=images/023.png >


# 待解决的问题

1、指纹库的继续完善：这是个旷日持久的工作，希望能坚持下去，我们也会持续的开源最新指纹库，希望大家手头有好的资源也可以贡献出来。

2、代理问题：虽然集成了代理功能，但经实际使用来看，搜集的免费代理质量还是差一些，速度会慢很多。

3、IP会被封：有的网站防护对目录枚举或一些路径非常敏感，会封IP地址；

4、下一步尝试对http头进行语义分析，从海量网站中提取分析header的共性，更高效的发现未知指纹。

# 小福利

1、指纹检测工具下载

我们把上面的13款**指纹识别工具**和搜集到的一些**论文资料**进行了汇总打包，大家可以直接下载。

`下载地址：https://pan.baidu.com/s/190K34cwjAWDUMLtR8EWvNA 提取码：5y4o 解压密码www.tidesec.net`

后续如有更新，会在我们公众号`TideSec安全团队`上提供下载，回复“指纹工具”即可获取最新指纹识别工具下载地址。

2、指纹库下载

最新指纹库的下载请关注我们公众号`TideSec安全团队`，回复“指纹库”即可获取最新指纹库下载地址。

# 关注我们

**TideSec安全团队：**

Tide安全团队正式成立于2019年1月，是以互联网攻防技术研究为目标的安全团队，目前聚集了十多位专业的安全攻防技术研究人员，专注于网络攻防、Web安全、移动终端、安全开发、IoT/物联网/工控安全等方向。

想了解更多Tide安全团队，请关注团队官网: http://www.TideSec.net 或关注公众号：

<div align=center><img src=images/ewm.png width=30% ></div>

