# 原创内容与第三方许可

本作的玩法代码、场景及基础贴图、音效和音乐采用原创或程序化生成流程。1.4.0 候选在六种既有贴图中加入本机模型生成的受限微细节，并在三条环境声中混入模型生成层。本仓库尚未为原创部分提供独立的开源许可证；其它使用许可请联系仓库作者。沿用 v1.0 发布说明：请勿将 demo 录屏用于商业发行。

生成模型来源：[Lykon / DreamShaper](https://huggingface.co/Lykon/DreamShaper)（本次 checkpoint 为 DreamShaper 8，作者模型页将许可标为 other，并指向 [Civitai 作者页](https://civitai.com/models/4384/dreamshaper)）；[Stability AI / Stable Audio Open 1.0](https://huggingface.co/stabilityai/stable-audio-open-1.0)（以该模型页链接的 License Agreement 为准）。这里只记录来源，不授予模型权重使用许可，也不声明生成内容具有排他权利。仓库保留本次生成源与参数供审看，不分发权重。生成与后处理记录见 [音画候选说明](docs/av_iteration_v1.4.md)。

Three.js 及所附 addons 依 MIT 许可分发，完整声明见 [vendor/three/LICENSE](vendor/three/LICENSE)。Windows 下载 ZIP 同时附带该声明。

1.5.0 候选另使用用户已下载的 [Comfy-Org Z-Image Turbo](https://huggingface.co/Comfy-Org/z_image_turbo) 在本机生成 11 份材质源，实际覆盖 16 个材质槽；Stable Audio Open 新生成两份声场并重混五条环境床。制作参数、原始生成源和实际运行证据见 [1.5 说明](docs/av_iteration_v1.5.md)。模型权重、账号与凭据不随仓库分发。

本仓库只包含游戏及其开发资料，不包含制作环境的账号、私人兴趣档案、原始会话或凭据。

1.6.0 返工沿用此前保存的 Z-Image 生成源，经重新配色、低频褪色与局部磨损处理；增加原创地毯、搪瓷和胶木表面，声音未再生成。详见 [1.6 制作说明](docs/av_iteration_v1.6.md)。
