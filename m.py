import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D

def draw_shelf(ax, width, depth, height, first_shelf_height, second_shelf_height, shelf_thickness):
    # 绘制货架的四个立柱
    columns_color = 'black'  # 加深框架颜色
    for dx in [0, width]:
        for dy in [0, depth]:
            ax.plot([dx, dx], [dy, dy], [0, height], color=columns_color, linewidth=2)  # 加粗线条

    # 画台板，增加透明度
    shelf_color = 'red'  # 台板颜色
    alpha_level = 0.5  # 透明度设置

    # 第一层台板
    x = np.array([0, width, width, 0])
    y = np.array([0, 0, depth, depth])
    z = np.array([first_shelf_height, first_shelf_height, first_shelf_height, first_shelf_height])
    z_upper = z + shelf_thickness
    vertices = np.column_stack((x, y, np.concatenate([z, z_upper])))
    ax.plot_trisurf(vertices[:, 0], vertices[:, 1], vertices[:, 2], color=shelf_color, alpha=alpha_level)

    # 第二层台板
    z = np.array([first_shelf_height + second_shelf_height, first_shelf_height + second_shelf_height,
                  first_shelf_height + second_shelf_height, first_shelf_height + second_shelf_height])
    z_upper = z + shelf_thickness
    vertices = np.column_stack((x, y, np.concatenate([z, z_upper])))
    ax.plot_trisurf(vertices[:, 0], vertices[:, 1], vertices[:, 2], color=shelf_color, alpha=alpha_level)

    # 标注尺寸
    ax.text(width / 2, -0.2, 0, f"Width: {width}m", color='black', horizontalalignment='center')
    ax.text(width + 0.1, depth / 2, 0, f"Depth: {depth}m", color='black', verticalalignment='center', rotation=270)
    ax.text(width + 0.1, depth + 0.1, height / 2, f"Height: {height}m", color='black', rotation=315)

# 创建一个3D坐标系
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# 货架尺寸和参数
width = 1.5
depth = 1.2
height = 1.6
first_shelf_height = 0.1
second_shelf_height = 1.5
shelf_thickness = 0.02

# 绘制货架
draw_shelf(ax, width, depth, height, first_shelf_height, second_shelf_height, shelf_thickness)

# 设置视角
ax.view_init(elev=20, azim=-75)  # 调整视图角度和方向

# 显示图形
plt.show()
