/**
 * Convert canvas image to subsampled (original size)
 */
function convertCanvas(ctx, xres, yres) {
    let inputXRes = xres * 10
    let imgData = ctx.getImageData(0, 0, 320, 80)
    let pixels = imgData.data

    // 4 bit depth (RGBA)
    pixels = pixels.filter((el, inx) => {
        return Math.floor(inx / (inputXRes * 4)) % 10 == 0 // Every 10th row in y
    })

    pixels = pixels.filter((el, inx) => {
        return (inx % 40) < 4 // Every 10th pixel in x
    })

    // ctx.putImageData(new ImageData(pixels, 32, 8), 0, 0) // Post-rendered preview
    
    var buff = new Uint8Array(xres * yres * 2)
    for (var y = 0; y < yres; y++) {
        for (var x = 0; x < xres; x++) {
            let r = pixels[(x + y * xres) * 4 + 0] >> 3
            let g = pixels[(x + y * xres) * 4 + 1] >> 2
            let b = pixels[(x + y * xres) * 4 + 2] >> 3
            let rgb = r | (g << 5) | (b << 11)
            buff[(y * xres + x) * 2 + 0] = rgb & 255
            buff[(y * xres + x) * 2 + 1] = rgb >> 8
        }
    }
    return buff;
}

/**
 * Send array to webserver for displaying
 */
async function send(buff) {
    console.log('sending data')
    let req = new XMLHttpRequest()
    req.open("POST", "/draw", true)
    req.setRequestHeader("Accept-Language", "")
    req.setRequestHeader("Accept", "")
    await req.send(buff)
}