import sensor, image, time, ustruct
from pyb import UART, LED
class KalmanFilter:
	def __init__(self, process_noise=1e-2, measurement_noise=1, estimate_error=1, initial_value=0):
		self.q = process_noise
		self.r = measurement_noise
		self.p = estimate_error
		self.x = initial_value
	def update(self, measurement):
		self.p += self.q
		k = self.p / (self.p + self.r)
		self.x += k * (measurement - self.x)
		self.p *= (1 - k)
		return self.x
uart = UART(1, 115200)
uart.init(115200, bits=8, parity=None, stop=1)
led3 = LED(3)
led3.off()
def send_uart_packet(number, x, y):
	try:
		checksum =( 0xAA + 0x06 + number + x + y)  & 0xFF
		data = ustruct.pack("<BBBBBB",
						   0xAA,
						   0x06,
						   number,
						   x,
						   y,
						   checksum)
		uart.write(data)
		print("send successfully")
	except Exception as e:
		print(f"error: {e}")
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QQVGA)
sensor.set_contrast(3)
num_quantity = 8
num_model = []
for n in range(1, num_quantity+1):
	num_model.append(image.Image(str(n) + '.pgm'))
clock = time.clock()
img_to_matching = sensor.alloc_extra_fb(35, 45, sensor.GRAYSCALE)
threshold = (0, 70)
scale = 1
kf_x = KalmanFilter()
kf_y = KalmanFilter()
is_recognized = False
last_recognize_time = 0
led_on_duration = 500
while(True):
	clock.tick()
	img = sensor.snapshot()
	img_gray = img.to_grayscale(copy=True)
	blobs = img_gray.find_blobs([threshold])
	current_time = time.ticks_ms()
	recognize_success = False
	if blobs:
		for blob in blobs:
			if blob.pixels() > 60 and 100 > blob.h() > 10 and blob.w() > 2:
				cx = int(kf_x.update(blob.cx()))
				cy = int(kf_y.update(blob.cy()))
				scale = 40 / blob.h()
				try:
					img_to_matching.draw_image(
						img_gray,
						0, 0,
						roi=(blob.x()-2, blob.y()-2, blob.w()+4, blob.h()+4),
						x_scale=scale,
						y_scale=scale
					)
				except Exception:
					continue
				for n in range(0, num_quantity):
					r = img_to_matching.find_template(num_model[n], 0.7, step=2, search=image.SEARCH_EX)
					if r:
						img.draw_rectangle(blob.x()-2, blob.y()-2, blob.w()+4, blob.h()+4, color=(255,0,0), thickness=4)
						img.draw_string(cx-5, cy-5, str(n+1), scale=4, color=(255,0,0))
						print(f"num={n+1}, X={cx}, Y={cy}, FPS={clock.fps()}")
						send_uart_packet(n+1, cx, cy)
						recognize_success = True
						last_recognize_time = current_time
						break
				if recognize_success:
					break
	if recognize_success:
		led3.on()
	else:
		if current_time - last_recognize_time > led_on_duration:
			led3.off()