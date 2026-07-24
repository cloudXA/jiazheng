import { analyzeContractRisk, transcribeAudio } from '../../services/ai'
import { saveRiskCase } from '../../services/cases'
import { RiskAnalysis } from '../../services/types'

const ASSISTANT_DRAFT_KEY = 'risk-assistant-draft'
const recorderManager = wx.getRecorderManager()

interface AssistantData {
  input: string
  cursorPosition: number
  recording: boolean
  transcribing: boolean
  analyzing: boolean
  result: RiskAnalysis | null
  transcriptionNote: string
  saved: boolean
}

interface TextInputEvent {
  detail: {
    value: string
    cursor: number
  }
}

interface TextBlurEvent {
  detail: {
    cursor: number
  }
}

Component({
  data: {
    input: '',
    cursorPosition: 0,
    recording: false,
    transcribing: false,
    analyzing: false,
    result: null,
    transcriptionNote: '',
    saved: false,
  } as AssistantData,
  lifetimes: {
    attached() {
      recorderManager.onStart(() => {
        this.setData({
          recording: true,
          transcriptionNote: '正在录音，讲完后点击“结束录音”。',
        })
      })
      recorderManager.onStop((recording) => {
        this.handleRecordingStop(recording.tempFilePath)
      })
      recorderManager.onError(() => {
        this.setData({ recording: false, transcribing: false })
        wx.showToast({ title: '录音失败，请改用文字录入', icon: 'none' })
      })
    },
  },
  methods: {
    onShow() {
      const tabBar = this.getTabBar() as any
      if (tabBar) tabBar.setData({ selected: 1 })

      const draft = wx.getStorageSync(ASSISTANT_DRAFT_KEY) as string
      if (draft) {
        this.setData({
          input: draft,
          cursorPosition: draft.length,
          result: null,
          saved: false,
        })
        wx.removeStorageSync(ASSISTANT_DRAFT_KEY)
      }
    },
    onInput(e: TextInputEvent) {
      this.setData({
        input: e.detail.value,
        cursorPosition: e.detail.cursor,
        result: null,
        saved: false,
      })
    },
    onInputBlur(e: TextBlurEvent) {
      this.setData({ cursorPosition: e.detail.cursor })
    },
    onUseExample() {
      const example =
        '客户王女士找住家保姆，先试工7天。阿姨是合作方推荐的，' +
        '电话中说好成功后收首月工资30%的服务费，但客户还没有微信确认，' +
        '退款和不得私签的规则也没有说清楚。'
      this.setData({
        input: example,
        cursorPosition: example.length,
        result: null,
        saved: false,
        transcriptionNote: '',
      })
    },
    onClearInput() {
      this.setData({
        input: '',
        cursorPosition: 0,
        result: null,
        saved: false,
        transcriptionNote: '',
      })
    },
    onRecordTap() {
      if (this.data.transcribing) return
      if (this.data.recording) {
        recorderManager.stop()
        return
      }

      wx.getSetting({
        success: (settings) => {
          if (settings.authSetting['scope.record']) {
            this.startRecording()
            return
          }
          wx.authorize({
            scope: 'scope.record',
            success: () => this.startRecording(),
            fail: () => {
              wx.showModal({
                title: '需要录音权限',
                content: '请在设置中允许使用麦克风，或直接使用文字录入。',
                confirmText: '去设置',
                success: (modal) => {
                  if (modal.confirm) wx.openSetting()
                },
              })
            },
          })
        },
      })
    },
    startRecording() {
      recorderManager.start({
        duration: 60000,
        sampleRate: 16000,
        numberOfChannels: 1,
        format: 'wav',
      })
    },
    async handleRecordingStop(tempFilePath: string) {
      this.setData({
        recording: false,
        transcribing: true,
        transcriptionNote: '录音已保存，正在转成文字…',
      })
      try {
        const transcription = await transcribeAudio(tempFilePath)
        const insertPosition = Math.min(
          Math.max(this.data.cursorPosition, 0),
          this.data.input.length,
        )
        const input =
          this.data.input.slice(0, insertPosition) +
          transcription.text +
          this.data.input.slice(insertPosition)
        this.setData({
          input,
          cursorPosition: insertPosition + transcription.text.length,
          result: null,
          saved: false,
          transcriptionNote: transcription.simulated
            ? '当前为开发模拟转写；接入后端语音服务后会使用真实录音内容。'
            : '语音已转成文字，请核对后再分析。',
        })
      } catch (error) {
        const message = error instanceof Error ? error.message : '语音转写失败'
        this.setData({ transcriptionNote: `${message}，录音未丢失。` })
        wx.showToast({ title: message, icon: 'none' })
      } finally {
        this.setData({ transcribing: false })
      }
    },
    async onAnalyze() {
      const sourceText = this.data.input.trim()
      if (this.data.analyzing || this.data.transcribing || this.data.recording) return
      if (sourceText.length < 8) {
        wx.showToast({ title: '请至少描述客户、服务和收费情况', icon: 'none' })
        return
      }

      this.setData({ analyzing: true, result: null, saved: false })
      try {
        const result = await analyzeContractRisk(sourceText)
        this.setData({ result })
      } catch {
        // 错误提示已在请求层统一处理
      } finally {
        this.setData({ analyzing: false })
      }
    },
    onCopyMessage() {
      const result = this.data.result
      if (!result) return
      wx.setClipboardData({
        data: result.confirmationMessage,
        success: () => wx.showToast({ title: '确认话术已复制', icon: 'success' }),
      })
    },
    onSave() {
      const result = this.data.result
      if (!result) return
      saveRiskCase(result)
      this.setData({ saved: true })
      wx.showToast({ title: '已保存到工作台', icon: 'success' })
    },
    onReset() {
      this.setData({
        input: '',
        cursorPosition: 0,
        result: null,
        saved: false,
        transcriptionNote: '',
      })
    },
  },
})
