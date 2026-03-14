# Maintainer: Piratheon <piratheon@github.com>

pkgname=aion-dl
_pkgname=Aion-dl
pkgver=1.0.0
pkgrel=1
pkgdesc="A full-featured GTK4/Adwaita frontend for yt-dlp"
arch=('any')
url="https://github.com/Piratheon/Aion-dl"
license=('GPL3')
depends=('python-gobject' 'libadwaita' 'yt-dlp' 'ffmpeg')
makedepends=('python-setuptools' 'python-build' 'python-installer' 'python-wheel')
source=("$_pkgname-$pkgver.tar.gz") # Placeholder source
sha256sums=('SKIP')

build() {
    cd "$_pkgname-$pkgver"
    python -m build --wheel --no-isolation
}

package() {
    cd "$_pkgname-$pkgver"
    python -m installer --destdir="$pkgdir" dist/*.whl

    # Desktop entry
    install -Dm644 assets/aion-dl.desktop "$pkgdir/usr/share/applications/aion-dl.desktop"

    # Icon
    install -Dm644 assets/io.github.piratheon.aion-dl.png "$pkgdir/usr/share/pixmaps/io.github.piratheon.aion-dl.png"
}
