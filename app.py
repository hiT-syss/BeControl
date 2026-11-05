import copy
import json
import os
import sys
import time
from pathlib import Path
from queue import Empty

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout,
    QLineEdit, QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

from hand_picker import HandPicker
from kamera_gozlemci import Camera, GESTURES, HANDS
from oyun_tetikleyici import KEYS, Trigger, is_focused, open_windows
from ui_widgets import STYLE, CameraPreview, TitleBar, button, card, label

ASSETS = Path(__file__).resolve().parent
STORE = (Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
         / 'BeControl' / 'profiles.json') if getattr(sys, 'frozen', False) else ASSETS / 'profiller.json'
DEFAULT = {'Spider-Man': {'steering': True, 'bindings': [
    ['Red', 9, ['w', 'shift'], 'Hold'],
    ['Red', 3, ['space'], 'Press'],
    ['Green', 0, ['left click'], 'Repeat'],
    ['Green', 2, ['right click'], 'Press'],
    ['Green', 1, ['f'], 'Press'],
]}}
MODE_LABELS = {'Press': 'Press once', 'Hold': 'Hold down', 'Repeat': 'Repeat'}


def combo(items=()):
    widget = QComboBox()
    widget.addItems(items)
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    widget.setMinimumWidth(0)
    widget.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    return widget


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().hide()
            item.widget().deleteLater()


class App(QWidget):
    def __init__(self, store=STORE):
        super().__init__()
        self.store = Path(store)
        self.setWindowIcon(QIcon(str(ASSETS / 'BeControl.ico')))
        self.setWindowTitle('BeControl • Play with motion')
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(1000, 700)
        self.resize(1220, 840)
        self.setMouseTracking(True)
        self.camera = None
        self.latest = None
        self.camera_error = ''
        self.armed = False
        self.trigger = Trigger()
        self.windows = {}
        self.keys = []
        self.read_error = ''
        self.profiles = self.load_profiles()
        self.build()
        self.refresh_profiles()
        self.refresh_windows()
        if self.read_error:
            self.notify(self.read_error)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(25)
        self.stop_shortcut = QShortcut(QKeySequence('Esc'), self)
        self.stop_shortcut.activated.connect(self.disarm)

    def load_profiles(self):
        source = self.store
        if not source.exists() and getattr(sys, 'frozen', False):
            source = Path(sys.executable).with_name('profiller.json')
        if not source.exists():
            return copy.deepcopy(DEFAULT)
        try:
            profiles = json.loads(source.read_text(encoding='utf-8-sig'))
            if not isinstance(profiles, dict):
                raise ValueError('Invalid profile list.')
            for name, profile in profiles.items():
                if not isinstance(name, str) or not isinstance(profile, dict):
                    raise ValueError('Invalid profile format.')
                if not isinstance(profile.get('bindings'), list):
                    raise ValueError('Invalid key bindings.')
                for index, (side, mask, keys, mode) in enumerate(profile['bindings']):
                    side = {'Kırmızı': 'Red', 'Yeşil': 'Green'}.get(side, side)
                    mode = {'Bas': 'Press', 'Tut': 'Hold', 'Tekrarla': 'Repeat'}.get(mode, mode)
                    mouse_names = {'sol tık': 'left click', 'sağ tık': 'right click', 'orta tık': 'middle click'}
                    if isinstance(keys, list):
                        keys = [mouse_names.get(key, key) for key in keys]
                    if (side not in HANDS or mask not in GESTURES or mode not in MODE_LABELS
                            or not isinstance(keys, list) or not keys or any(key not in KEYS for key in keys)):
                        raise ValueError('A key binding is invalid.')
                    profile['bindings'][index] = [side, mask, keys, mode]
                profile.setdefault('steering', False)
            return profiles
        except (OSError, ValueError, TypeError) as error:
            self.read_error = f'Unable to load profiles. The original file has been preserved. {error}'
            return copy.deepcopy(DEFAULT)

    def build(self):
        self.setStyleSheet(STYLE)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        shell = QFrame()
        shell.setObjectName('shell')
        outer.addWidget(shell)
        body = QVBoxLayout(shell)
        body.setContentsMargins(12, 0, 12, 12)
        body.setSpacing(0)
        titlebar = TitleBar()
        titlebar.setFixedHeight(54)
        top = QHBoxLayout(titlebar)
        top.setContentsMargins(12, 0, 12, 0)
        for color, name, action in (
            ('#ed7b7b', 'Close', self.close),
            ('#e6bf62', 'Minimize', self.showMinimized),
            ('#82cba5', 'Maximize / restore', self.toggle_maximize),
        ):
            control = button('', action)
            control.setFixedSize(14, 14)
            control.setToolTip(name)
            control.setAccessibleName(name)
            control.setStyleSheet(f'QPushButton {{ background: {color}; border-radius: 7px; padding: 0; }}')
            top.addWidget(control)
        top.addStretch()
        top.addWidget(label('BeControl', 'muted'))
        top.addStretch()
        top.addSpacing(66)
        body.addWidget(titlebar)
        content = QHBoxLayout()
        content.setSpacing(0)
        body.addLayout(content, 1)

        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(198)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 28, 16, 20)
        side.setSpacing(10)
        brand = label('BeControl', 'subtitle')
        brand.setStyleSheet('font-size: 24px; color: #6f5ac4; font-weight: 700;')
        side.addWidget(brand)
        side.addWidget(label('Turn motion into play.', 'muted', True))
        side.addSpacing(28)
        side.addWidget(label('WORKSPACE', 'eyebrow'))
        self.nav_group = QButtonGroup(self)
        for index, text in enumerate(('◉   Play', '＋   Create game')):
            nav = button(text, role='nav')
            nav.setCheckable(True)
            nav.clicked.connect(lambda checked=False, page=index: self.change_page(page))
            self.nav_group.addButton(nav, index)
            side.addWidget(nav)
        self.nav_group.button(0).setChecked(True)
        side.addSpacing(24)
        side.addWidget(label('GAME PROFILE', 'eyebrow'))
        self.profile_box = combo()
        self.profile_box.setAccessibleName('Game profile')
        self.profile_box.currentTextChanged.connect(self.profile_changed)
        side.addWidget(self.profile_box)
        side.addStretch()
        side.addWidget(label('BeControl  /  DESKTOP', 'eyebrow'))
        content.addWidget(sidebar)

        main = QVBoxLayout()
        main.setContentsMargins(28, 16, 20, 6)
        main.setSpacing(14)
        content.addLayout(main, 1)
        self.heading = label('Play with your hands', 'title')
        self.description = label('Choose your game, turn on the camera, and take control.', 'muted', True)
        main.addWidget(self.heading)
        main.addWidget(self.description)
        self.pages = QStackedWidget()
        main.addWidget(self.pages, 1)
        self.pages.addWidget(self.build_play())
        self.pages.addWidget(self.build_editor())
        self.notice = label('', 'notice', True)
        self.notice.hide()
        main.addWidget(self.notice)

    def build_play(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(16)
        split = QHBoxLayout()
        split.setSpacing(16)
        layout.addLayout(split, 1)
        camera_card, view = card()
        header = QHBoxLayout()
        header.addWidget(label('Live camera', 'subtitle'))
        header.addStretch()
        self.camera_badge = label('○  Off', 'muted')
        header.addWidget(self.camera_badge)
        view.addLayout(header)
        self.preview = CameraPreview()
        view.addWidget(self.preview, 1)
        hands = QHBoxLayout()
        self.hand_labels = {}
        for name, color in (('Red', '#d3697e'), ('Green', '#3f9c7d')):
            info = label(f'●  {name}\nWaiting for a hand', wrap=True)
            info.setStyleSheet(f'color: {color}; font-size: 12px;')
            hands.addWidget(info, 1)
            self.hand_labels[name] = info
        view.addLayout(hands)
        view.addWidget(label('Mirrored view · Left hand is red, right hand is green.', 'muted', True))
        split.addWidget(camera_card, 1)

        settings, form = card()
        settings.setFixedWidth(280)
        form.addWidget(label('Get ready to play', 'subtitle'))
        form.addSpacing(4)
        form.addWidget(label('01  GAME WINDOW', 'eyebrow'))
        self.window_box = combo()
        self.window_box.setAccessibleName('Open game window to control')
        self.window_box.currentIndexChanged.connect(self.disarm)
        form.addWidget(self.window_box)
        form.addWidget(button('↻  Refresh open windows', self.refresh_windows))
        form.addSpacing(10)
        form.addWidget(label('02  CAMERA', 'eyebrow'))
        self.camera_box = combo(('Camera 1', 'Camera 2', 'Camera 3', 'Camera 4'))
        self.camera_box.setAccessibleName('Camera selection')
        form.addWidget(self.camera_box)
        self.camera_button = button('Turn camera on', self.toggle_camera)
        form.addWidget(self.camera_button)
        form.addStretch()
        self.status = label('Your camera is off.', 'muted', True)
        form.addWidget(self.status)
        self.play_button = button('▶  Start control', self.toggle_armed, 'primary')
        self.play_button.setMinimumHeight(46)
        form.addWidget(self.play_button)
        form.addWidget(label('Switch to your selected game after starting.', 'muted', True))
        split.addWidget(settings)
        footer, notes = card()
        row = QHBoxLayout()
        row.addWidget(label('Gestures in this profile', 'subtitle'))
        row.addStretch()
        row.addWidget(button('Edit hotkeys  →', lambda: self.change_page(1)))
        notes.addLayout(row)
        self.binding_summary = label('', 'muted', True)
        notes.addWidget(self.binding_summary)
        layout.addWidget(footer)
        return page

    def build_editor(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 6, 8, 6)
        layout.setSpacing(14)
        scroll.setWidget(page)
        project, create = card()
        create.setContentsMargins(18, 14, 18, 14)
        row = QHBoxLayout()
        row.addWidget(label('New game project', 'subtitle'))
        self.project_name = QLineEdit()
        self.project_name.setPlaceholderText('Project name, e.g. Spider-Man')
        self.project_name.setAccessibleName('New project name')
        self.project_name.setMaxLength(80)
        self.project_name.returnPressed.connect(self.new_profile)
        row.addWidget(self.project_name, 1)
        row.addWidget(button('＋  Create', self.new_profile, 'primary'))
        create.addLayout(row)
        layout.addWidget(project)

        mapping, edit = card()
        title_row = QHBoxLayout()
        title_row.addWidget(label('Hotkeys', 'subtitle'))
        title_row.addStretch()
        title_row.addWidget(label('One gesture → your chosen keys', 'muted'))
        edit.addLayout(title_row)
        columns = QHBoxLayout()
        columns.setSpacing(24)
        edit.addLayout(columns)
        gesture_panel = QVBoxLayout()
        gesture_panel.setSpacing(10)
        columns.addLayout(gesture_panel, 1)
        side_row = QHBoxLayout()
        self.side_group = QButtonGroup(self)
        for index, name in enumerate(HANDS):
            toggle = button(f'●  {name} hand', role='segment')
            toggle.setCheckable(True)
            self.side_group.addButton(toggle, index)
            toggle.clicked.connect(self.side_changed)
            side_row.addWidget(toggle)
        self.side_group.button(0).setChecked(True)
        gesture_panel.addLayout(side_row)
        self.hand = HandPicker()
        self.hand.setMinimumHeight(260)
        self.hand.maskChanged.connect(self.gesture_changed)
        gesture_panel.addWidget(self.hand)
        presets = QHBoxLayout()
        for title, mask in (('Fist', 0), ('Palm', 15), ('V sign', 3), ('Swing', 9)):
            preset = button(title)
            preset.setStyleSheet('padding: 7px 8px; font-size: 11px;')
            preset.clicked.connect(lambda checked=False, value=mask: self.hand.setMask(value))
            presets.addWidget(preset)
        gesture_panel.addLayout(presets)
        gesture_panel.addWidget(label('Click the fingers you want to hold open.', 'muted', True))

        assign = QVBoxLayout()
        assign.setSpacing(10)
        columns.addLayout(assign, 1)
        assign.addWidget(label('SELECTED GESTURE', 'eyebrow'))
        self.gesture_title = label('', 'subtitle', True)
        assign.addWidget(self.gesture_title)
        assign.addWidget(label('Assign keys', wrap=True))
        key_row = QHBoxLayout()
        self.key_box = combo(KEYS)
        self.key_box.setEditable(True)
        self.key_box.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.key_box.setCurrentText('shift')
        self.key_box.setAccessibleName('Keyboard key or mouse button to assign')
        key_row.addWidget(self.key_box, 1)
        key_row.addWidget(button('＋ Add', self.add_key))
        assign.addLayout(key_row)
        self.key_chips = QGridLayout()
        self.key_chips.setSpacing(6)
        assign.addLayout(self.key_chips)
        assign.addWidget(label('Add multiple keys to press them together.', 'muted', True))
        assign.addSpacing(5)
        assign.addWidget(label('How should it press?'))
        self.mode_box = combo(MODE_LABELS.values())
        self.mode_box.setAccessibleName('Key press mode')
        self.mode_box.currentIndexChanged.connect(self.update_mode_help)
        assign.addWidget(self.mode_box)
        self.mode_help = label('', 'muted', True)
        assign.addWidget(self.mode_help)
        assign.addStretch()
        self.save_button = button('Save binding', self.save_binding, 'primary')
        assign.addWidget(self.save_button)
        assign.addWidget(label('Saving replaces the binding for this hand and gesture.', 'muted', True))
        layout.addWidget(mapping)

        saved, saved_layout = card()
        saved_layout.addWidget(label('Saved bindings', 'subtitle'))
        self.bindings_layout = QVBoxLayout()
        self.bindings_layout.setSpacing(8)
        saved_layout.addLayout(self.bindings_layout)
        self.steering = QCheckBox('Steer the camera with the red wrist while swinging')
        self.steering.toggled.connect(self.save_steering)
        saved_layout.addWidget(self.steering)
        layout.addWidget(saved)
        layout.addStretch()
        self.hand.setMask(4)
        self.gesture_changed(4)
        self.update_mode_help()
        self.render_keys()
        return scroll

    def toggle_maximize(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.isMaximized():
            point = event.position()
            edges = Qt.Edge(0)
            if point.x() < 9:
                edges |= Qt.Edge.LeftEdge
            if point.x() > self.width() - 9:
                edges |= Qt.Edge.RightEdge
            if point.y() < 9:
                edges |= Qt.Edge.TopEdge
            if point.y() > self.height() - 9:
                edges |= Qt.Edge.BottomEdge
            if edges:
                self.windowHandle().startSystemResize(edges)

    def change_page(self, index):
        self.disarm()
        self.pages.setCurrentIndex(index)
        self.nav_group.button(index).setChecked(True)
        self.heading.setText(('Play with your hands', 'Create your controls')[index])
        self.description.setText(('Choose your game, turn on the camera, and take control.',
                                  'Create a project. Map hand gestures to your chosen keys.')[index])

    def notify(self, text):
        self.notice.setText(text)
        self.notice.setVisible(bool(text))

    def current(self):
        return self.profiles.get(self.profile_box.currentText())

    def persist(self, updated):
        try:
            if self.read_error:
                self.notify('The profile file could not be read. Repair it before saving.')
                return False
            self.store.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.store.with_suffix('.tmp')
            temporary.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(self.store)
        except OSError as error:
            self.notify(f'Unable to save. {error}')
            return False
        self.profiles = updated
        return True

    def refresh_profiles(self, selected=None):
        name = selected or self.profile_box.currentText()
        self.profile_box.blockSignals(True)
        self.profile_box.clear()
        self.profile_box.addItems(self.profiles)
        if name in self.profiles:
            self.profile_box.setCurrentText(name)
        self.profile_box.blockSignals(False)
        self.profile_changed()

    def profile_changed(self):
        self.disarm()
        self.keys = []
        self.render_keys()
        self.render_bindings()

    def render_bindings(self):
        clear_layout(self.bindings_layout)
        profile = self.current()
        bindings = profile['bindings'] if profile else []
        self.steering.blockSignals(True)
        self.steering.setChecked(bool(profile and profile['steering']))
        self.steering.blockSignals(False)
        self.steering.setEnabled(bool(profile))
        self.save_button.setEnabled(bool(profile))
        if not bindings:
            self.bindings_layout.addWidget(label('Add your first gesture above.', 'muted'))
        for index, (side, mask, keys, mode) in enumerate(bindings):
            row = QWidget()
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 0, 0, 0)
            motion = label(f'●  {side}  ·  {GESTURES[mask]}', wrap=True)
            motion.setStyleSheet('color: #bf6476;' if side == HANDS[0] else 'color: #398e73;')
            line.addWidget(motion, 2)
            line.addWidget(label(' + '.join(keys).upper(), wrap=True), 1)
            line.addWidget(label(MODE_LABELS[mode], 'muted'))
            line.addWidget(button('Edit', lambda checked=False, i=index: self.load_binding(i)))
            remove = button('×', lambda checked=False, i=index: self.remove_binding(i), 'danger')
            remove.setAccessibleName(f'Delete {side} {GESTURES[mask]} binding')
            line.addWidget(remove)
            self.bindings_layout.addWidget(row)
        names = [f'{GESTURES[mask]} → {" + ".join(keys).upper()}' for side, mask, keys, mode in bindings]
        self.binding_summary.setText('   ·   '.join(names) or 'No bindings yet. Add your first gesture in Create game.')

    def new_profile(self):
        name = self.project_name.text().strip()
        if not name:
            self.project_name.setFocus()
            self.notify('Enter a name for your game project first.')
            return
        if name.casefold() in {key.casefold() for key in self.profiles}:
            self.notify('This project name is already in use. Choose another name.')
            return
        updated = copy.deepcopy(self.profiles)
        updated[name] = {'steering': False, 'bindings': []}
        if self.persist(updated):
            self.refresh_profiles(name)
            self.project_name.clear()
            self.notify(f'{name} created. You can now assign keys to hand gestures.')

    def side_changed(self):
        self.hand.setSide(HANDS[self.side_group.checkedId()])
        self.gesture_changed(self.hand.mask)

    def gesture_changed(self, mask):
        self.gesture_title.setText(f'{HANDS[self.side_group.checkedId()]} hand · {GESTURES[mask]}')

    def update_mode_help(self):
        self.mode_help.setText(('Press once when you make the gesture.',
                                'Hold the key for as long as you keep the gesture.',
                                'Press repeatedly while you keep the gesture.')[self.mode_box.currentIndex()])

    def add_key(self):
        key = self.key_box.currentText().strip().lower()
        if key not in KEYS:
            self.notify('Choose a valid key or mouse button from the list.')
            return
        if key not in self.keys:
            self.keys.append(key)
        self.render_keys()

    def render_keys(self):
        clear_layout(self.key_chips)
        if not self.keys:
            self.key_chips.addWidget(label('For a single key, you can save directly.', 'muted', True), 0, 0, 1, 3)
        for index, key in enumerate(self.keys):
            chip = button(f'{key.upper()}  ×', lambda checked=False, value=key: self.remove_key(value), 'chip')
            chip.setAccessibleName(f'Remove {key} from the key combination')
            self.key_chips.addWidget(chip, index // 3, index % 3)

    def remove_key(self, key):
        self.keys.remove(key)
        self.render_keys()

    def save_binding(self):
        if not self.current():
            return
        keys = list(self.keys) or [self.key_box.currentText().strip().lower()]
        if any(key not in KEYS for key in keys):
            self.notify('Choose a valid key from the list.')
            return
        self.disarm()
        side, mask = HANDS[self.side_group.checkedId()], self.hand.mask
        updated = copy.deepcopy(self.profiles)
        bindings = updated[self.profile_box.currentText()]['bindings']
        bindings[:] = [entry for entry in bindings if entry[:2] != [side, mask]]
        bindings.append([side, mask, keys, tuple(MODE_LABELS)[self.mode_box.currentIndex()]])
        if self.persist(updated):
            self.render_bindings()
            self.notify(f'{side} hand · {GESTURES[mask]} → {" + ".join(keys).upper()} saved.')

    def load_binding(self, index):
        side, mask, keys, mode = self.current()['bindings'][index]
        self.side_group.button(HANDS.index(side)).setChecked(True)
        self.hand.setSide(side)
        self.hand.setMask(mask)
        self.gesture_changed(mask)
        self.keys = list(keys)
        self.key_box.setCurrentText(keys[0])
        self.mode_box.setCurrentIndex(tuple(MODE_LABELS).index(mode))
        self.render_keys()
        self.pages.widget(1).verticalScrollBar().setValue(0)

    def remove_binding(self, index):
        self.disarm()
        updated = copy.deepcopy(self.profiles)
        del updated[self.profile_box.currentText()]['bindings'][index]
        if self.persist(updated):
            self.render_bindings()
            self.notify('Binding removed.')

    def save_steering(self, enabled):
        if self.current():
            self.disarm()
            updated = copy.deepcopy(self.profiles)
            updated[self.profile_box.currentText()]['steering'] = enabled
            self.persist(updated)
            self.render_bindings()

    def refresh_windows(self):
        self.disarm()
        previous = self.window_box.currentData()
        self.windows = open_windows()
        self.window_box.blockSignals(True)
        self.window_box.clear()
        self.window_box.addItem('Choose a game window', None)
        for name, target in self.windows.items():
            self.window_box.addItem(name.rsplit('  [', 1)[0], target)
        for index in range(self.window_box.count()):
            if self.window_box.itemData(index) == previous:
                self.window_box.setCurrentIndex(index)
                break
        self.window_box.blockSignals(False)

    def toggle_camera(self):
        if self.camera:
            self.disarm()
            self.camera.stop.set()
            self.camera_button.setText('Turning camera off…')
            self.camera_button.setEnabled(False)
        else:
            self.latest = None
            self.camera_error = ''
            self.camera = Camera(self.camera_box.currentIndex())
            self.camera.start()
            self.camera_box.setEnabled(False)
            self.camera_button.setText('Turn camera off')

    def toggle_armed(self):
        if self.armed:
            self.disarm()
            return
        if not self.current() or not self.current()['bindings']:
            self.notify('Add at least one gesture and key in Create game.')
        elif not self.window_box.currentData():
            self.notify('Choose the open game window you want to control.')
        elif not self.latest or time.monotonic() - self.latest[3] > 0.45 or self.camera.stop.is_set():
            self.notify('Turn on the camera and wait for the preview first.')
        else:
            self.armed = True
            self.play_button.setText('■  Stop control')
            self.notify('Ready. Switch to your selected game. Keys are released when you return here.')

    def disarm(self, *_):
        self.armed = False
        self.trigger.reset()
        if hasattr(self, 'play_button'):
            self.play_button.setText('▶  Start control')

    def tick(self):
        status = self.camera_error or 'Your camera is off.'
        new_frame = False
        if self.camera:
            status = 'Starting camera…'
            if not self.camera.is_alive():
                self.camera_error = self.camera.error or ''
                status = self.camera_error or 'Your camera is off.'
                self.disarm()
                self.camera = self.latest = None
                self.camera_button.setText('Turn camera on')
                self.camera_button.setEnabled(True)
                self.camera_box.setEnabled(True)
                self.preview.clear()
            else:
                try:
                    self.latest = self.camera.frames.get_nowait()
                    new_frame = True
                except Empty:
                    pass
        now = time.monotonic()
        fresh = self.camera and not self.camera.stop.is_set() and self.latest and now - self.latest[3] < 0.45
        self.camera_badge.setText('●  Live' if fresh else '○  Off')
        if fresh:
            rgb, gestures, tilt, _ = self.latest
            if new_frame:
                self.preview.set_frame(rgb)
            for side, info in self.hand_labels.items():
                info.setText(f'●  {side}\n{GESTURES.get(gestures[side], "Waiting for a hand")}')
            status = 'Camera ready. You can start control.'
            if self.armed:
                target = self.window_box.currentData()
                if is_focused(tuple(target) if target else None):
                    status = 'Control active. Your gestures are controlling the game.'
                    try:
                        profile = self.current()
                        self.trigger.update(profile['bindings'], gestures, tilt, profile['steering'] and new_frame, now)
                    except Exception as error:
                        self.disarm()
                        self.notify(f'Unable to send input. {error}')
                else:
                    self.trigger.reset()
                    status = 'Control ready. Switch to your selected game window.'
        else:
            self.trigger.reset()
            for side, info in self.hand_labels.items():
                info.setText(f'●  {side}\nWaiting for a hand')
            if self.latest:
                self.preview.clear()
                status = 'Waiting for video. Keys have been released.'
        self.status.setText(status)

    def closeEvent(self, event):
        self.timer.stop()
        self.disarm()
        if self.camera:
            self.camera.stop.set()
            self.camera.join(timeout=1.0)
        event.accept()


if __name__ == '__main__':
    application = QApplication(sys.argv)
    application.setStyle('Fusion')
    application.setFont(QFont('Segoe UI', 10))
    window = App()
    available = application.primaryScreen().availableGeometry()
    window.resize(min(1220, available.width() - 40), min(840, available.height() - 40))
    window.move(available.center() - window.rect().center())
    window.show()
    sys.exit(application.exec())
