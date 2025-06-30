# FantechX9ThorDriver

### 🔧 Requirements / Dependencies

· Python 3  
· Gtk3 & gobject-introspection  
· Module pyusb  

### 🚀 Langkah-langkah / Installation / Usage

Follow these steps:

### 1. Clone the repository
```bash
git clone https://github.com/muharamdani/FantechX9ThorDriver.git
```
enter the dir
```bash
cd FantechX9ThorDriver
```

### 2. Install required Python module  
```bash
pip install pyusb
```
Or if you use Arch Linux: 
```bash
yay -S python-pyusb
```

### 3. Run the script  
```bash
python3 driver_frontend.py
```

### 🔗 **Menjadikan aplikasi ini app desktop (`.desktop`)**

Follow these steps:

### 1. Open your terminal
type
```bash
cd ~/
```
### 2. Create a `.desktop` file

Create a file named `fantech-x9.desktop` and add the following content:

```bash
[Desktop Entry]
Name=Fantech X9 Driver
Comment=Frontend app to control Fantech X9 mouse
Exec=python3 ~/FantechX9ThorDriver/driver_frontend.py
Icon=mouse
Terminal=false
Type=Application
Categories=Utility;
```
Save & exit

### 3. Copy file yout .desktop file
```bash
cp fantech-x9.desktop ~/.local/share/applications/
```
then
```bash
chmod +x ~/.local/share/applications/fantech-x9.desktop
```

### 4. Launch the app

✅Done!

