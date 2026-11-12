# Koi Through the Torii

![coolest-art-01](https://make.fun/badge/coolest-art-01.svg)
![rank](https://make.fun/badge/coolest-art-01/rank/overtheraadot.svg)
![reward](https://make.fun/badge/coolest-art-01/reward/overtheraadot.svg)

A colossal glowing koi leaps through a vermilion torii gate under a
crescent moon — one bold image, drawn entirely in code.

## The piece

A white-and-orange koi arcs out of still water and through the gate at
dusk: deep indigo sky, a glowing crescent moon, drifting cherry-blossom
petals, mountain silhouettes, and the moon's shimmer on the water. Big
shapes, a limited palette, no text — it reads at a glance and still hits
at 300 px.

## How it is made

`main.py` draws the whole image procedurally with the Python 3 standard
library only (a small scanline rasterizer: circles, polygons, gradients,
radial glow, Bezier spine) and encodes the PNG with `zlib`. No external
files, no network, no randomness beyond a fixed seed — run it twice and
the bytes are identical.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Writes `out/entry.png` (1024x1024, under 1 MiB). Without
`MAKEFUN_OUTPUT_DIR` it writes to `/output`, as the competition runs it.

## License

MIT — see [LICENSE](LICENSE).
