# All Right Reserved!!
# 2024/09/28 Harrison Chen <harrison.mm.chen@gmail.com>
import os, sys, requests, re, time, random
from PySide6 import QtGui
from PySide6.QtWidgets import QApplication, QWidget, QTableView, QGridLayout, QMessageBox, QAbstractItemView, QMenu
from PySide6.QtCore import Qt, QObject, QAbstractTableModel, QModelIndex, QThread, QTimer, QEvent, QPoint
from PySide6.QtGui import QFont, QCursor
import webbrowser, platform
import qdarktheme
import chrome_bookmarks
from bs4 import BeautifulSoup
from dataclasses import dataclass
import pickle
from functools import partial
import yt_dlp
from datetime import datetime
#import debugpy

@dataclass
class VIDEO_CLIP:
    ChannelName: str
    State: str
    ShowTime: str
    Title: str
    URL: str
    WontCheck: bool

def fCloseWig(wig:QWidget):
    wig.close()
    wig.deleteLater()

def ShowAutoClosedMsgBox(title:str,msg:str,showMS:int,parent=None):
    wig = QMessageBox(parent)
    wig.setIcon(QMessageBox.Icon.Information)
    wig.setText(msg+f'\n\n\n本訊息 {showMS/1000.0:g} 秒後會自動關閉')
    wig.setWindowTitle(title)
    wig.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    #msg.setDetailedText(f"{ret['details']}")
    wig.setStandardButtons(QMessageBox.StandardButton.Close)
    QTimer.singleShot(showMS,partial(fCloseWig,wig))
    wig.show()

def GetTrickUrl(st:VIDEO_CLIP)->bool:
    response = requests.get(st.URL)
    response.encoding = 'utf8'
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')
    search_string = re.compile(r'"title":\{"accessibility":\{"accessibilityData":\{')
    found_strings = soup.find_all(string=search_string)
    for found_string in found_strings:
        matchBadge = re.findall(r'"simpleText":"(.*?)"', found_string)
        if matchBadge:
            st.Title = matchBadge[1]
            st.ShowTime = f'即將直播' if f'即將直播' in matchBadge else matchBadge[2]
            return True
    return False

def get_relative_time(timestamp):
    if not timestamp:
        return "未知時間"
    
    # 計算秒數差
    seconds_diff = int(time.time() - timestamp)
    
    # 定義時間間隔（秒）
    minute = 60
    hour = 3600
    day = 86400
    month = 2592000  # 以 30 天計
    year = 31536000
    
    if seconds_diff < minute:
        return f"{seconds_diff} 秒前"
    elif seconds_diff < hour:
        return f"{seconds_diff // minute} 分鐘前"
    elif seconds_diff < day:
        return f"{seconds_diff // hour} 小時前"
    elif seconds_diff < month:
        return f"{seconds_diff // day} 天前"
    elif seconds_diff < year:
        return f"{seconds_diff // month} 個月前"
    else:
        return f"{seconds_diff // year} 年前"

def get_latest_video_title(st:VIDEO_CLIP)->bool:
    """
    使用 yt-dlp 獲取 YouTube 頻道最新影片的標題。
    """
    # 設定 yt-dlp 參數
    ydl_opts = {
        'quiet': True,              # 不輸出處理日誌
        'no_warnings': True,        # 隱藏警告訊息
        'extract_flat': True,       # 僅提取列表資訊，不解析完整影片內容（速度極快）
        #'extract_flat': 'in_playlist',  # 最快模式：不解析單獨影片
        'playlist_items': '1',      # 僅獲取最新的一項
        'dump_single_json': True,   # 回傳單一 JSON 格式
        'extractor_args': {'youtube':{'lang':['zh-TW']}}, # 強制指定 YouTube 提取器的語係為 繁體中文 (zh-TW)
        'http_headers': {'Accept-Language':'zh-TW;q=0.9,en;q=0.8'}, # 額外保險：在 HTTP Header 中也加入語系偏好
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 獲取頻道資訊
            info = ydl.extract_info(st.URL, download=False, process=False)
            # 解析第一支影片的標題
            first_entry = next(info['entries'])
            st.Title = first_entry['title']
            video_url = first_entry['url']
            # 2. 針對該影片抓取完整細節
            video_info = ydl.extract_info(video_url, download=False)
            st.ShowTime = video_info.get('live_status')
            # 可能的值：'is_upcoming' (即將直播), 'is_live' (正在直播), 'was_live' (直播重播), None (一般影片)
            match st.ShowTime:
                case 'is_upcoming': st.ShowTime = f'即將直播'
                case 'is_live': st.ShowTime = f'正在直播'
                case 'was_live':st.ShowTime = f'直播重播'
                case 'not_live'|None:
                    st.ShowTime = f'一般影片'
                    seconds = video_info.get('timestamp')
                    if seconds:
                        st.ShowTime = get_relative_time(seconds)
                    else:
                        st.ShowTime += f'時間未知'
            return True
            #info = ydl.extract_info(st.URL, download=False)
            #if 'entries' in info and len(info['entries']) > 0:
            #    latest_video = info['entries'][0]
            #    st.Title = latest_video.get('title')
            #    st.ShowTime = latest_video.get('live_status')
            #    # 可能的值：'is_upcoming' (即將直播), 'is_live' (正在直播), 'was_live' (直播重播), None (一般影片)
            #    match st.ShowTime:
            #        case 'is_upcoming': st.ShowTime = f'即將直播'
            #        case 'is_live': st.ShowTime = f'正在直播'
            #        case 'was_live':st.ShowTime = f'直播重播'
            #        case None|'not_live':
            #            st.ShowTime = f'一般影片'
            #            seconds = latest_video.get('upload_date')
            #            if seconds:
            #                #seconds = int(seconds)
            #                #hours, remainder = divmod(seconds, 3600)
            #                #minutes, seconds = divmod(remainder, 60)
            #                #st.ShowTime = f"{hours}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes}:{seconds:02d}"
            #                st.ShowTime = to_relative_time(seconds)
            #            else:
            #                st.ShowTime += f'時間長度未知'
            #    return True
    except Exception as e:
        st.Title = f"發生錯誤: {e}"
        pass
    return False

def GetVideoTitleFromUrl(st:VIDEO_CLIP)->bool:
    if st.URL.find(f'channel') != -1:
        return GetTrickUrl(st)
    return get_latest_video_title(st)
    response = requests.get(st.URL)
    response.encoding = 'utf8'
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')
    search_string = re.compile(r'"title":\{"runs":\[\{"text":"')
    found_strings = soup.find_all(string=search_string)
    for found_string in found_strings:
        #match = re.search(r'"text":"(.*?)"', found_string)
        match = re.search(r'\{"text":"(.*?)"\}', found_string)
        matchBadge = re.findall(r'"simpleText":"(.*?)"', found_string)
        if match:
            st.Title = match.group(1).replace('\\"','"')
            st.ShowTime = f'即將直播' if f'即將直播' in matchBadge else matchBadge[0]
            if st.Title.find('{') == -1:
                return True
    return False

class YChannelModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.m_listAll = []
        self.m_loadedItems = []
        self.m_downloadTitle = []
        self.m_ColumnNames = list(VIDEO_CLIP.__dataclass_fields__.keys())
        self.fetchCount = 0
        self.HoverRow = -1
        self.HoverCol = -1
    def setHoverItem(self, row, col):
        if self.HoverRow != -1 and self.HoverCol != -1:
            idx = self.index(self.HoverRow, self.HoverCol, QModelIndex())
            self.dataChanged.emit(idx, idx)
        self.HoverRow = row
        self.HoverCol = col
        if self.HoverRow != -1 and self.HoverCol != -1:
            idx = self.index(self.HoverRow, self.HoverCol, QModelIndex())
            self.dataChanged.emit(idx, idx)
    def getChannelStructByName(self, ch_name:str) -> tuple[VIDEO_CLIP, int]:
        for row in range(len(self.m_listAll)):
            if self.m_listAll[row].ChannelName == ch_name:
                return self.m_listAll[row], row
        return None
    def getChannelStruct(self, row:int) -> VIDEO_CLIP:
        if row < len(self.m_listAll):
            return self.m_listAll[row]
        return None
    def getChannelState(self, row:int) -> VIDEO_CLIP:
        if row < len(self.m_listAll):
            return self.m_listAll[row].State
        return None
    def getDownloadTitle(self, row:int)->str:
        if row < len(self.m_downloadTitle):
            return self.m_downloadTitle[row]
        return None
    def canFetchMore(self, parent) -> bool:
        if parent.isValid():
            return False
        return self.fetchCount < len(self.m_listAll)
    def fetchMore(self, parent) -> None:
        if parent.isValid():
            return
        start = self.fetchCount
        remainder = len(self.m_listAll) - start
        if remainder > 20: itemsToFetch = 20
        else: itemsToFetch = remainder
        if itemsToFetch <= 0:
            return
        self.beginInsertRows(QModelIndex(), start, start + itemsToFetch - 1)
        self.fetchCount += itemsToFetch
        self.endInsertRows()
    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return self.fetchCount
    def columnCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.m_ColumnNames)
    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole):
        match role:
            case Qt.DisplayRole:
                if orientation == Qt.Horizontal:
                    if self.m_ColumnNames[section] == f'WontCheck':
                        return f'不檢查'
                    return self.m_ColumnNames[section]
                if orientation == Qt.Vertical:
                    return str(section + 1)
            case Qt.TextAlignmentRole:
                return Qt.AlignVCenter + Qt.AlignLeft
        return None
    def flags(self, index: QModelIndex):
        flags = Qt.ItemIsEnabled
        if self.m_ColumnNames[index.column()] == f'WontCheck':
            flags |= Qt.ItemIsUserCheckable
        return flags
    def setData(self, index: QModelIndex, value, role:Qt.ItemDataRole):
        row = index.row()
        col = index.column()
        match role:
            case Qt.CheckStateRole:
                if self.m_ColumnNames[col] == f'WontCheck':
                    self.m_listAll[row].WontCheck=bool(value)
                    self.dataChanged.emit(index, index)
                    return True
            case Qt.EditRole:
                if value is not None and self.m_ColumnNames[col] == f'WontCheck':
                    self.m_listAll[row].WontCheck=value
                    self.dataChanged.emit(index, index)
                    return True
        #self.dataChanged.emit(index, index)
        return False
    def sort(self, column, order=Qt.AscendingOrder):
        #super().sort(column, order)
        #self.layoutAboutToBeChanged.emit()
        self.modelAboutToBeReset.emit()
        attr_name = self.m_ColumnNames[column]
        bf_ch = [st.ChannelName for st in self.m_listAll]
        bf_title = self.m_downloadTitle.copy()
        self.m_listAll.sort(
            key=lambda x: getattr(x, attr_name),
            reverse=(order == Qt.DescendingOrder)
        )
        self.m_downloadTitle.clear()
        for row in range(len(self.m_listAll)):
            bf_ch_idx=-1
            try:
                bf_ch_idx=bf_ch.index(self.m_listAll[row].ChannelName)
            except ValueError:
                continue
            self.m_downloadTitle.append(bf_title[bf_ch_idx])
        #self.layoutChanged.emit()
        self.modelReset.emit()
    def data(self, index: QModelIndex, role:Qt.ItemDataRole):
        if not index.isValid():
            return None
        #item = index.internalPointer()
        row = index.row()
        col = index.column()
        match role:
            case Qt.DisplayRole:
                strRet=''
                try:
                    if self.m_ColumnNames[col] != f'WontCheck':
                        val = getattr(self.m_listAll[row], self.m_ColumnNames[col])
                        strRet=str(val)
                except Exception as e:
                    print(f'{e}')
                    pass
                return strRet
            case Qt.TextAlignmentRole:
                val = Qt.AlignVCenter
                return val + Qt.AlignLeft
            case Qt.ForegroundRole:
                if col == 3:
                    if getattr(self.m_listAll[row], self.m_ColumnNames[1]) == f'有新片':
                        return QtGui.QColor('red')
            case Qt.FontRole:
                if self.HoverRow == row and self.HoverCol == col:
                    #if col == 1:
                    #    if getattr(self.m_listAll[row], self.m_ColumnNames[1]) != f'有新片':
                    #        return None
                    _f = QFont()
                    _f.setUnderline(True)
                    return _f
            case Qt.CheckStateRole:
                if self.m_ColumnNames[col] == f'WontCheck':
                    return Qt.Checked if  self.m_listAll[row].WontCheck else Qt.Unchecked
                return None
        return None
    def removeRow(self, row: int, parent) -> bool:
        return self.removeRows(row,1,parent)
    def removeRows(self, position, rows=1, index=QModelIndex()):
        self.beginRemoveRows(index, position, position + rows - 1)
        bRet = True
        for i in range(rows):
            del self.m_listAll[position+i]
            self.fetchCount -= 1
        self.endRemoveRows()
        return bRet
    def SaveList(self):
        for row in range(len(self.m_listAll)):
            st = self.m_listAll[row]
            selected_item = next((itemC for itemC in self.m_loadedItems if itemC.ChannelName == st.ChannelName), None)
            if selected_item and st.State != f'設為已看':
                st.Title = selected_item.Title
            else:
                st.Title = self.m_downloadTitle[row]
        try:
            with open('chk.pkl', 'wb') as file:
                pickle.dump(self.m_listAll, file)
        except Exception as e:
            print(f'{e}')
            pass
    def LoadFromBookmark(self):
        for url in chrome_bookmarks.urls:
            if 'youtube' in url.url:
                if ('@' in url.url and 'videos' in url.url) or 'channel' in url.url or 'streams' in url.url:
                    sName = url.name.replace(f" - YouTube", f'')
                    self.m_listAll.append(VIDEO_CLIP(State=f'在書籤中', ChannelName=sName, Title=f'', ShowTime=f'', URL=url.url, WontCheck=False))
        try:
            with open('chk.pkl', 'rb') as file:
                self.m_loadedItems = pickle.load(file)
        except Exception as e:
            pass
        missChannel = []
        for row in range(len(self.m_loadedItems)):
            item = self.m_loadedItems[row]
            selected_item = next((itemC for itemC in self.m_listAll if itemC.ChannelName == item.ChannelName), None)
            if selected_item is None:
                item.State = f'在記錄襠中'
                item.WontCheck=True
                missChannel.append(item.ChannelName)
                self.m_listAll.append(item)
        if len(missChannel) != 0:
            allName = f"{','.join(missChannel)}".replace(',', "\n")
            ShowAutoClosedMsgBox(f'書籤遺失記錄', f' 有在記錄襠中，但未在Chrome的書籤中\n之頻道名稱:\n\n' + allName, 30000)
        self.modelReset.emit()
    def Redraw(self, row:int, col:int):
        cidx = self.index(row,col,QModelIndex())
        self.dataChanged.emit(cidx,cidx)
    def RedrawState(self, row:int):
        self.Redraw(row,1)
    def RedrawTitle(self, row:int):
        self.Redraw(row,3)
    def RedrawShowTime(self, row:int):
        self.Redraw(row,2)
    def checkTitle(self, row:int, item:VIDEO_CLIP):
        item.State = f'檢查中'
        self.RedrawState(row)
        if GetVideoTitleFromUrl(item):
            title = item.Title
            selected_item = next((itemC for itemC in self.m_loadedItems if itemC.ChannelName == item.ChannelName), None)
            if selected_item and selected_item.Title != item.Title:
                item.State = f'有新片'
                item.Title = f'舊:' + selected_item.Title + f'\n新:' + item.Title
            else:
                item.State = f'未更新'
            self.RedrawTitle(row)
            self.RedrawShowTime(row)
        else:
            item.State = f'失敗'
    def CheckTitles(self):
        try:
            for row in range(len(self.m_listAll)):
                item = self.m_listAll[row]
                selected_item = next((itemC for itemC in self.m_loadedItems if itemC.ChannelName == item.ChannelName), None)
                if selected_item:
                    item.State = f'已看' if selected_item.State == f'設為已看' else f"前次觀看"
                    item.WontCheck = selected_item.WontCheck
                    self.RedrawState(row)
                    item.Title = selected_item.Title
                    self.RedrawTitle(row)
        except Exception as e:
            pass
        self.m_downloadTitle.clear()
        for row in range(len(self.m_listAll)):
            item = self.m_listAll[row]
            title = f''
            if item.WontCheck:
                item.State = f'不檢查'
                title = item.Title
            else:
                item.State = f'檢查中'
                self.RedrawState(row)
                #if GetVideoTitleFromUrl(item.ChannelName, item.URL, item.Title, item.ShowTime):
                if GetVideoTitleFromUrl(item):
                    title = item.Title
                    selected_item = next((itemC for itemC in self.m_loadedItems if itemC.ChannelName == item.ChannelName), None)
                    if selected_item and selected_item.Title != item.Title:
                        item.State = f'有新片'
                        item.Title = f'舊:' + selected_item.Title + f'\n新:' + item.Title
                    else:
                        item.State = f'未更新'
                    self.RedrawTitle(row)
                    self.RedrawShowTime(row)
                else:
                    item.State = f'失敗'
                #self.checkTitle(row,item)
                #title = item.Title
                time.sleep(random.uniform(0.1, 2.1))
            self.RedrawState(row)
            self.m_downloadTitle.append(title)

class ExtBrowser(QThread):
    def __init__(self, name, url:str, parent=None):
        super().__init__(parent)
        curOS = platform.system()
        if curOS == "Windows":
            self.location = 'C:/Program Files/Google/Chrome/Application/chrome.exe %s --incognito'
        elif curOS == "Darwin":
            self.location = 'open -a /Applications/Google\ Chrome.app --args --incognito %s'
        elif curOS == "Linux":
            self.location = '/usr/bin/google-chrome %s --incognito'
        self.name = name
        self.url = url
        self.state = 'init'
        self.start_2_run()
    def start_2_run(self):
        self.start()
        for i in range(6):
            self.wait(200)
            if not self.isRunning():
                break
    def run(self):
        self.state = 'is_mine'
        webbrowser.get(self.location).open(self.url, new=2)
        self.state = 'background'
    def second_run(self, url):
        if self.isRunning():
            webbrowser.get(self.location).open(url, new=2)
        else:
            self.url = url
            self.start_2_run()
    def quit(self):
        super().quit()
        self.terminate()

class YChannelTableView(QTableView):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.horizontalHeader().setStyleSheet('QHeaderView::section{padding-right:12px;}')
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        #self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.customContextMenuRequested.connect(self.on_ViewCellMenu)
        #self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.PointingHandOn = False
        self.modelHover = None
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.installEventFilter(self)
        self.m_Update1stRow = None
        self.clicked.connect(self.on_clicked)
        self._ExtB = None
        self.cntOn = 0
        self.cntOff= 0
    def setHoverStat(self, on:bool, row, col):
        if on == False:
            if self.PointingHandOn == True:
                self.modelHover.setHoverItem(-1, -1)
                QApplication.restoreOverrideCursor()
                self.PointingHandOn = False
                self.modelHover = None
        else:
            self.modelHover.setHoverItem(row, col)
            if self.PointingHandOn == False:
                QApplication.setOverrideCursor(Qt.PointingHandCursor)
                self.PointingHandOn = True
    def eventFilter(self, obj: QObject, ev: QEvent):
        match ev.type():
            case QEvent.HoverEnter|QEvent.HoverMove:
                if obj is not self: return super().eventFilter(obj,ev)
                #pos = self.ui.tableViewHistory.mapFromGlobal(QCursor.pos())
                view_pos = obj.viewport().mapFromGlobal(QCursor.pos())
                modelIndex = obj.indexAt(view_pos) #ev.position().toPoint())
                model = modelIndex.model()
                if hasattr(model, 'sourceModel'):
                    # We are a proxy model
                    model = modelIndex.model().sourceModel()
                    modelIndex = modelIndex.model().mapToSource(modelIndex)
                if not hasattr(model, 'setHoverItem'):
                    self.setHoverStat(False, -1, -1)
                    return super().eventFilter(obj,ev)
                row = modelIndex.row()
                col = modelIndex.column()
                self.modelHover = model
                HoverOn = False
                if col <= 1:
                    HoverOn = True
                    if col == 1:
                        item = self.modelHover.getChannelStruct(row)
                        if item.State != f'有新片' or item.ShowTime == f'即將直播':
                            HoverOn = False
                if HoverOn is True:
                    self.setHoverStat(True, row, col)
                else:
                    self.setHoverStat(False, -1, -1)
                return super().eventFilter(obj,ev)
            case QEvent.HoverLeave:
                self.setHoverStat(False, -1, -1)
                return super().eventFilter(obj,ev)
        return super().eventFilter(obj,ev)
    def setModel(self, model) -> None:
        super().setModel(model)
        self.model().dataChanged.connect(self.onDataChanged)
        self.model().modelReset.connect(self.fetchAll)
    def setDefaultColumnWidth(self, width:int):
        self.setColumnWidth(0, width * 2 /10)
        self.setColumnWidth(1, width * 0.6 /10)
        self.setColumnWidth(2, width * 0.8 /10)
        self.setColumnWidth(3, width * 6.0 /10)
        self.setColumnWidth(5, width * 0.6 /10)
        self.hideColumn(4)
    def fetchAll(self):
        model = self.model()
        while model.canFetchMore(QModelIndex()):
            model.fetchMore(QModelIndex())
        self.resizeRowsToContents()
    def makeRowVisable(self, row:int):
        index = self.model().index(row, 0)
        self.resizeRowToContents(row)
        self.scrollTo(index)
    def onDataChanged(self, topLeft:QModelIndex, bottomRight:QModelIndex, role):
        row = topLeft.row()
        if self.m_Update1stRow is None:
            if topLeft.column() == 1:
                if self.model().data(topLeft, Qt.DisplayRole) == f'有新片':
                    self.m_Update1stRow = row
        self.resizeRowToContents(row)
        self.scrollTo(self.model().index(row, 0))
    def Finished(self):
        row = self.m_Update1stRow if self.m_Update1stRow else 0
        #self.scrollTo(self.model().index(row, 0, QModelIndex()))
        self.model().RedrawState(row)
        self.setSortingEnabled(True)
    def resizeTableView(self, width:int):
        #self.resizeColumnsToContents()
        self.setDefaultColumnWidth(width-6)
        self.resizeRowsToContents()
    def WaitCursorOn(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.cntOn += 1
    def on_TimerWaitCursorOff(self):
        if self.cntOff != self.cntOn:
            QApplication.restoreOverrideCursor()
            self.cntOff += 1
    def LaunchURL(self,name,url):
        self.WaitCursorOn()
        if self._ExtB is None:self._ExtB = ExtBrowser(name,url,self)
        else:self._ExtB.second_run(url)
        QTimer.singleShot(0, self.on_TimerWaitCursorOff)
    def on_clicked(self,x:QModelIndex):
        model = x.model()
        if hasattr(model, 'sourceModel'):
            model = x.model().sourceModel()
            x = x.model().mapToSource(x)
        if x.column() == 0:
            item = model.getChannelStruct(x.row())
            if item:
                self.LaunchURL(f'{x.row()}', item.URL)
        elif x.column() == 1:
            row = x.row()
            item = model.getChannelStruct(row)
            if item.State == f'有新片' and item.ShowTime != f'即將直播':
                item.State = f'設為已看'
                item.Title = self.model().getDownloadTitle(row)
                self.resizeRowToContents(row)
    def on_ViewCellMenu(self,p:QPoint,widget=None,menu:QMenu=None):
        idx = self.indexAt(p)
        model = idx.model()
        if hasattr(model, 'sourceModel'):
            model = idx.model().sourceModel()
            idx = idx.model().mapToSource(idx)
        if widget is None: widget = self.sender()
        if isinstance(widget, QAbstractItemView):
            widget = widget.viewport()
        if menu is None: menu = QMenu()
        else: menu.addSeparator()
        channel = ''
        # listS = []
        # for idxx in self.selectedIndexes():
        #     rowIdx = model.index(idxx.row(),0,QModelIndex())
        #     s = model.data(rowIdx,Qt.DisplayRole)
        #     if not s in listS:
        #         listS.append(s)
        #         channel += f':{s}'
        item = model.getChannelStruct(idx.row())
        if item is None: return
        channel = item.ChannelName
        action = menu.addAction(f'自記錄襠中刪除:{channel}')
        action.triggered.connect(self.on_menuRow_triggered)
        menu.exec(widget.mapToGlobal(p))
    def on_menuRow_triggered(self, checked):
        action = self.sender()
        if action.text().startswith(f'自記錄襠中刪除'):
            # rows = set()
            # for idx in self.selectedIndexes():
            #     rows.add(idx.row())
            # for row in sorted(rows, reverse=True):
            #     self.model().removeRow(row,QModelIndex())
            listChnl = action.text().split(':')
            listChnl.remove('自記錄襠中刪除')
            for chName in listChnl:
                item, row = self.model().getChannelStructByName(chName)
                if row != -1:
                    self.model().removeRow(row,QModelIndex())
                    row = -1
    def closeEvent(self, event):
        if self._ExtB is not None:
            self._ExtB.quit()

class mGetTitleThread(QThread):
    def __init__(self, model:YChannelModel, view:YChannelTableView, parent=None):
        super().__init__(parent)
        self.m_model = model
        self.m_view = view
    def Redraw(self, row:int, col:int):
        cidx = self.m_model.index(row,col,QModelIndex())
        self.m_model.dataChanged.emit(cidx,cidx)
    def RedrawState(self, row:int):
        self.Redraw(row,1)
    def RedrawTitle(self, row:int):
        self.Redraw(row,2)
    def RedrawShowTime(self, row:int):
        self.Redraw(row,3)
    def run(self):
        #debugpy.debug_this_thread()
        self.m_model.CheckTitles()
        self.m_view.Finished()

class Window(QWidget):
    def __init__(self):
        super(Window, self).__init__()
        self.gridLayout = QGridLayout(self)
        self.gridLayout.setContentsMargins(2, 2, 2, 2)
        self.gridLayout.setSpacing(2)
        self.m_moduleY = YChannelModel(self)
        self.m_view = YChannelTableView(self)
        #self.m_moduleY.layoutChanged.connect(self.m_view.resizeRowsToContents)
        self.gridLayout.addWidget(self.m_view)
        self.m_view.setModel(self.m_moduleY)
        self.resize(1080, 720)
        self.m_view.resizeTableView(1080)
        self.setWindowTitle(f'有新的嗎?')
        self.m_moduleY.LoadFromBookmark()
        self.show()
        self.thread = mGetTitleThread(self.m_moduleY, self.m_view, self)
        self.thread.start()
    def closeEvent(self, event):
        self.thread.terminate()
        self.m_moduleY.SaveList()
        self.m_view.close()

os.chdir(os.path.dirname(os.path.realpath(__file__)))
app = QApplication(sys.argv)
qdarktheme.setup_theme(additional_qss="QToolTip{border:0px;}")
w = Window()
w.show()
app.exec()
