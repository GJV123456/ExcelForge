<script>
import { defineComponent, h, onBeforeUnmount, ref } from 'vue'
import { ElSelect } from 'element-plus'

let activeSelect = null

export default defineComponent({
  name: 'ExclusiveSelect',
  inheritAttrs: false,
  setup(_, { attrs, slots }) {
    const selectRef = ref(null)
    onBeforeUnmount(() => {
      if (activeSelect === selectRef.value) activeSelect = null
    })

    const handleVisibilityChange = (visible) => {
      const current = selectRef.value
      if (visible) {
        if (activeSelect && activeSelect !== current) activeSelect.blur()
        activeSelect = current
      } else if (activeSelect === current) {
        activeSelect = null
      }
      const listener = attrs.onVisibleChange
      if (Array.isArray(listener)) listener.forEach((handler) => handler(visible))
      else listener?.(visible)
    }

    return () => h(ElSelect, {
      ...attrs,
      ref: selectRef,
      onVisibleChange: handleVisibilityChange,
    }, slots)
  },
})
</script>
