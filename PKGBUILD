# Maintainer: Azteriisk <https://github.com/Azteriisk>
pkgname=omarchy-plugin-games-git
pkgver=1.1.0.r0
pkgrel=1
pkgdesc="Game launcher, library manager, Active Playspace, and Controller Steward for Omarchy"
arch=('any')
url="https://github.com/Azteriisk/omarchy-games"
license=('MIT')
depends=('python' 'python-evdev' 'quickshell')
optdepends=(
  'chromium: hardware-accelerated Xbox Cloud streaming'
  'libva-utils: hardware video decode verification via vainfo'
)
makedepends=('git')
provides=('omarchy-plugin-games')
conflicts=('omarchy-plugin-games')

_commit="2c577eabc7c1b5c572fdd725d59f94f9aa666412"
source=("git+https://github.com/Azteriisk/omarchy-games.git#commit=${_commit}")
md5sums=('SKIP')

package() {
  cd "$srcdir/omarchy-games"

  install -d "$pkgdir/usr/share/omarchy/plugins/azterisk.games"
  install -Dm644 manifest.json "$pkgdir/usr/share/omarchy/plugins/azterisk.games/manifest.json"
  install -Dm644 Service.qml "$pkgdir/usr/share/omarchy/plugins/azterisk.games/Service.qml"
  install -Dm644 BarWidget.qml "$pkgdir/usr/share/omarchy/plugins/azterisk.games/BarWidget.qml"
  install -Dm644 config.default.json "$pkgdir/usr/share/omarchy/plugins/azterisk.games/config.default.json"
  install -Dm755 scripts/omarchy-games "$pkgdir/usr/bin/omarchy-games"

  install -d "$pkgdir/usr/share/omarchy/plugins/azterisk.games/scripts"
  install -Dm755 scripts/games_scanner.py "$pkgdir/usr/share/omarchy/plugins/azterisk.games/scripts/games_scanner.py"
  install -Dm755 scripts/controller_steward.py "$pkgdir/usr/share/omarchy/plugins/azterisk.games/scripts/controller_steward.py"
  install -Dm755 scripts/playspace.py "$pkgdir/usr/share/omarchy/plugins/azterisk.games/scripts/playspace.py"
  install -Dm755 scripts/stream_runner.sh "$pkgdir/usr/share/omarchy/plugins/azterisk.games/scripts/stream_runner.sh"
  install -Dm644 scripts/omarchy-fix.js "$pkgdir/usr/share/omarchy/plugins/azterisk.games/scripts/omarchy-fix.js"

  if [ -d assets ]; then
    install -d "$pkgdir/usr/share/omarchy/plugins/azterisk.games/assets"
    install -Dm644 assets/* "$pkgdir/usr/share/omarchy/plugins/azterisk.games/assets/" 2>/dev/null || true
  fi

  install -Dm644 README.md "$pkgdir/usr/share/omarchy/plugins/azterisk.games/README.md"
  install -Dm755 install.sh "$pkgdir/usr/share/omarchy/plugins/azterisk.games/install.sh"
  install -Dm755 uninstall.sh "$pkgdir/usr/share/omarchy/plugins/azterisk.games/uninstall.sh"
}
