# Maintainer: Azteriisk <https://github.com/Azteriisk>
pkgname=omarchy-plugin-games-git
pkgver=1.0.0.r0
pkgrel=1
pkgdesc="Game launcher and library manager for Omarchy with Steam, Lutris, and RetroArch source indexing in the Apps menu and search bar."
arch=('any')
url="https://github.com/Azteriisk/omarchy-games"
license=('MIT')
depends=('python' 'quickshell')
makedepends=('git')
provides=('omarchy-plugin-games')
conflicts=('omarchy-plugin-games')

_commit="ae31e2b649fdb9b0e65196c4cd62e7bcc18be512"
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
  install -Dm755 scripts/games_scanner.py "$pkgdir/usr/share/omarchy/plugins/azterisk.games/scripts/games_scanner.py"
  install -Dm644 README.md "$pkgdir/usr/share/omarchy/plugins/azterisk.games/README.md"
  install -Dm755 install.sh "$pkgdir/usr/share/omarchy/plugins/azterisk.games/install.sh"
  install -Dm755 uninstall.sh "$pkgdir/usr/share/omarchy/plugins/azterisk.games/uninstall.sh"
}
